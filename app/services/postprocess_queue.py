"""Simple DB-backed postprocess job worker.

This module provides a polling worker that picks up pending jobs from the
`postprocess_jobs` table and runs `process_doc_once`. It implements simple
retry/backoff logic and marks jobs as `done` or `failed`.

This is intentionally lightweight and intended as an interim solution before
migrating to a broker-based queue.
"""
from datetime import datetime, timedelta
import time
import logging
from typing import Optional

from app.core.database import SessionLocal, PostprocessJob
from app.services.postprocess import process_doc_once

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 2.0  # seconds
BACKOFF_BASE_SECONDS = 5


def _acquire_job(db) -> Optional[PostprocessJob]:
    """Select a pending job and mark it in_progress atomically.

    Note: SQLite doesn't support SELECT ... FOR UPDATE, so we use a simple
    optimistic approach: select pending jobs ordered by next_attempt_at, then
    attempt to update the status to in_progress and commit. If commit fails due
    to concurrency, another worker will have claimed it.
    """
    now = datetime.utcnow()
    q = db.query(PostprocessJob).filter(
        PostprocessJob.status == "pending",
        (PostprocessJob.next_attempt_at == None) | (PostprocessJob.next_attempt_at <= now),
    ).order_by(PostprocessJob.created_at)

    job = q.first()
    if not job:
        return None

    try:
        job.status = "in_progress"
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.commit()
        # refresh
        db.refresh(job)
        return job
    except Exception:
        db.rollback()
        return None


def _mark_job_done(db, job: PostprocessJob):
    job.status = "done"
    job.updated_at = datetime.utcnow()
    db.add(job)
    db.commit()


def _mark_job_failed(db, job: PostprocessJob, error: str):
    job.attempts = job.attempts + 1
    job.last_error = error[:2000]
    job.updated_at = datetime.utcnow()
    if job.attempts >= job.max_attempts:
        job.status = "failed"
        db.add(job)
        db.commit()
        logger.error("Postprocess job %s failed permanently after %d attempts", job.id, job.attempts)
    else:
        # schedule next attempt with exponential backoff
        backoff = BACKOFF_BASE_SECONDS * (2 ** (job.attempts - 1))
        job.next_attempt_at = datetime.utcnow() + timedelta(seconds=backoff)
        job.status = "pending"
        db.add(job)
        db.commit()
        logger.info("Postprocess job %s scheduled retry in %s seconds (attempt %d)", job.id, backoff, job.attempts)


def enqueue_job_for_document(db, document_id: str, max_attempts: int = 5):
    job = PostprocessJob(document_id=document_id, status="pending", attempts=0, max_attempts=max_attempts)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job.id


def run_worker(poll_interval: float = DEFAULT_POLL_INTERVAL):
    """Run worker loop forever. Intended for manual start in development.

    In production, run this in a managed process and ensure proper logging/monitoring.
    """
    logger.info("Starting DB-backed postprocess worker with poll interval %s", poll_interval)
    while True:
        db = SessionLocal()
        try:
            job = _acquire_job(db)
            if not job:
                db.close()
                time.sleep(poll_interval)
                continue

            logger.info("Picked job %s for document %s", job.id, job.document_id)
            success, error = process_doc_once(job.document_id)
            if success:
                _mark_job_done(db, job)
                logger.info("Job %s completed", job.id)
            else:
                _mark_job_failed(db, job, error or "unknown error")
        except Exception:
            logger.exception("Worker encountered unexpected error")
        finally:
            try:
                db.close()
            except Exception:
                pass


if __name__ == "__main__":
    # Simple CLI entry for testing
    logging.basicConfig(level=logging.INFO)
    run_worker()
