"""Database-backed queue helpers for preference_jobs.

This module mirrors the structure of ``postprocess_queue`` but targets the
``preference_jobs`` table. Jobs are lightweight records processed by the
background personalization worker to keep preference profiles and cached
personalized scores up to date.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Sequence, Union

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.database import PreferenceJob, create_tables

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_SECONDS = 2.0
BACKOFF_BASE_SECONDS = 5
MAX_BACKOFF_SECONDS = 60
DEFAULT_MAX_ATTEMPTS = 3

PayloadType = Optional[Union[str, Dict[str, Any], Sequence[Any]]]


def _serialize_payload(payload: PayloadType) -> Optional[str]:
	if payload is None:
		return None
	if isinstance(payload, str):
		return payload
	try:
		return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
	except (TypeError, ValueError):
		logger.warning("personalization_queue: failed to serialize payload; dropping it")
		return None


def enqueue_job(
	db: Session,
	*,
	user_id: Optional[str] = None,
	document_id: Optional[str] = None,
	job_type: str = "profile_rebuild",
	payload: PayloadType = None,
	max_attempts: int = DEFAULT_MAX_ATTEMPTS,
	available_at: Optional[datetime] = None,
) -> str:
	"""Create a new preference job and return its identifier."""

	max_attempts = max(int(max_attempts or 0), 1)
	now = datetime.utcnow()
	job = PreferenceJob(
		user_id=user_id,
		document_id=document_id,
		job_type=job_type,
		status="pending",
		attempts=0,
		max_attempts=max_attempts,
		last_error=None,
		next_attempt_at=available_at,
		scheduled_at=available_at or now,
		created_at=now,
		updated_at=now,
		payload=_serialize_payload(payload),
	)
	db.add(job)
	db.commit()
	db.refresh(job)
	logger.debug(
		"personalization_queue: enqueued job %s (type=%s user=%s document=%s)",
		job.id,
		job.job_type,
		job.user_id,
		job.document_id,
	)
	return job.id


def enqueue_profile_update(
	db: Session,
	*,
	user_id: Optional[str] = None,
	document_id: Optional[str] = None,
	payload: PayloadType = None,
	max_attempts: int = DEFAULT_MAX_ATTEMPTS,
	available_at: Optional[datetime] = None,
) -> str:
	"""Convenience wrapper for profile rebuild jobs."""

	return enqueue_job(
		db,
		user_id=user_id,
		document_id=document_id,
		job_type="profile_rebuild",
		payload=payload,
		max_attempts=max_attempts,
		available_at=available_at,
	)


def _acquire_job(db: Session) -> Optional[PreferenceJob]:
	now = datetime.utcnow()
	query = (
		db.query(PreferenceJob)
		.filter(
			PreferenceJob.status == "pending",
			(PreferenceJob.next_attempt_at == None) | (PreferenceJob.next_attempt_at <= now),
		)
		.order_by(PreferenceJob.next_attempt_at.asc(), PreferenceJob.scheduled_at.asc(), PreferenceJob.created_at.asc())
	)
	job = query.first()
	if not job:
		return None
	try:
		job.status = "in_progress"
		job.updated_at = datetime.utcnow()
		db.add(job)
		db.commit()
		db.refresh(job)
		logger.debug("personalization_queue: leased job %s", job.id)
		return job
	except Exception:
		db.rollback()
		logger.debug("personalization_queue: failed to lease job %s due to concurrency", job.id)
		return None


def lease_job(db: Session) -> Optional[PreferenceJob]:
	"""Public helper to claim the next pending job."""

	return _acquire_job(db)


def mark_job_done(db: Session, job: PreferenceJob) -> None:
	job.status = "done"
	job.updated_at = datetime.utcnow()
	db.add(job)
	db.commit()
	logger.info("personalization_queue: job %s marked done", job.id)


def mark_job_failed(db: Session, job: PreferenceJob, error: str) -> None:
	job.attempts = int(job.attempts or 0) + 1
	job.last_error = (error or "")[:2000]
	job.updated_at = datetime.utcnow()

	if job.attempts >= (job.max_attempts or DEFAULT_MAX_ATTEMPTS):
		job.status = "failed"
		db.add(job)
		db.commit()
		logger.error(
			"personalization_queue: job %s reached max attempts (%s). Error: %s",
			job.id,
			job.attempts,
			error,
		)
		return

	backoff = BACKOFF_BASE_SECONDS * (2 ** (job.attempts - 1))
	backoff = min(backoff, MAX_BACKOFF_SECONDS)
	job.next_attempt_at = datetime.utcnow() + timedelta(seconds=backoff)
	job.status = "pending"
	db.add(job)
	db.commit()
	logger.info(
		"personalization_queue: job %s scheduled retry in %.1fs (attempt %s)",
		job.id,
		backoff,
		job.attempts,
	)


def schedule_profile_update(
	db: Session,
	*,
	user_id: Optional[str] = None,
	document_id: Optional[str] = None,
	payload: PayloadType = None,
	max_attempts: int = DEFAULT_MAX_ATTEMPTS,
	available_at: Optional[datetime] = None,
) -> Optional[str]:
	"""Best-effort helper that enqueues a profile update job with fallback handling."""

	try:
		return enqueue_profile_update(
			db,
			user_id=user_id,
			document_id=document_id,
			payload=payload,
			max_attempts=max_attempts,
			available_at=available_at,
		)
	except OperationalError:
		logger.debug("personalization_queue: tables missing when scheduling profile update; attempting create_tables()")
		try:
			create_tables()
		except Exception:
			logger.exception("personalization_queue: create_tables failed while scheduling profile update")
		try:
			return enqueue_profile_update(
				db,
				user_id=user_id,
				document_id=document_id,
				payload=payload,
				max_attempts=max_attempts,
				available_at=available_at,
			)
		except Exception:
			logger.exception("personalization_queue: failed to enqueue profile update after ensuring tables")
	except Exception:
		logger.exception("personalization_queue: failed to enqueue profile update")
	return None


__all__ = [
	"DEFAULT_POLL_INTERVAL_SECONDS",
	"BACKOFF_BASE_SECONDS",
	"enqueue_job",
	"enqueue_profile_update",
	"schedule_profile_update",
	"lease_job",
	"mark_job_done",
	"mark_job_failed",
]
