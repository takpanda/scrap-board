from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
from sqlalchemy import text
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _load_sources_and_schedule():
    """Read sources from DB and schedule jobs."""
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT id, name, cron_schedule, enabled FROM sources WHERE enabled=1"))
        for r in rows.fetchall():
            sid = r[0]
            cron = r[2]
            job_id = f"fetch_source_{sid}"
            # remove existing job if present
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass
            if cron:
                try:
                    trigger = CronTrigger.from_crontab(cron)
                    scheduler.add_job(_run_fetch_for_source, trigger=trigger, id=job_id, args=[sid], replace_existing=True)
                    logger.info(f"Scheduled source {sid} with cron {cron}")
                except Exception:
                    logger.exception(f"Failed to schedule source {sid} cron {cron}")
    finally:
        db.close()


def _run_fetch_for_source(source_id: int):
    logger.info(f"Triggering fetch for source {source_id} at {datetime.utcnow().isoformat()}")
    try:
        # Import here to avoid circular import at module load
        from app.services.ingest_worker import trigger_fetch_for_source

        trigger_fetch_for_source(source_id)
    except Exception:
        logger.exception("Failed to run fetch for source")


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
    _load_sources_and_schedule()


def stop_scheduler():
    try:
        # Only shutdown if scheduler is running to avoid SchedulerNotRunningError
        if getattr(scheduler, "running", False):
            scheduler.shutdown()
        else:
            logger.debug("Scheduler not running; skip shutdown")
    except Exception:
        logger.exception("Failed to shutdown scheduler")
