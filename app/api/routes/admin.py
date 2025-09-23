from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from typing import List

from app.core.database import SessionLocal, PostprocessJob
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Add a local to_jst filter so templates rendered via this module can format JST
def to_jst(dt, fmt: str = "%Y-%m-%d %H:%M"):
    if not dt:
        return ""
    try:
        if getattr(dt, 'tzinfo', None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if ZoneInfo is not None:
            jst = dt.astimezone(ZoneInfo("Asia/Tokyo"))
        else:
            jst = dt.astimezone(timezone(timedelta(hours=9)))
        return jst.strftime(fmt)
    except Exception:
        try:
            return dt.strftime(fmt)
        except Exception:
            return ""

templates.env.filters["to_jst"] = to_jst


def _get_jobs(limit: int = 100, status: str = None) -> List[PostprocessJob]:
    db = SessionLocal()
    try:
        q = db.query(PostprocessJob).order_by(PostprocessJob.created_at.desc())
        if status:
            # allow comma-separated list
            allowed = {s.strip() for s in status.split(',') if s.strip()}
            if allowed:
                q = q.filter(PostprocessJob.status.in_(list(allowed)))
        q = q.limit(limit)
        return q.all()
    finally:
        db.close()


@router.get("/admin/postprocess_jobs", response_class=HTMLResponse)
def admin_postprocess_jobs(request: Request, limit: int = 100, status: str = None):
    jobs = _get_jobs(limit=limit, status=status)
    now = datetime.utcnow()
    def seconds_remaining(job):
        if job.next_attempt_at is None:
            return 0
        delta = job.next_attempt_at - now
        return int(delta.total_seconds())

    jobs_ctx = [
        {
            "id": job.id,
            "document_id": job.document_id,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "next_attempt_at": job.next_attempt_at,
            "last_error": job.last_error,
            "seconds_remaining": seconds_remaining(job),
            "created_at": job.created_at,
        }
        for job in jobs
    ]

    return templates.TemplateResponse(
        "admin_postprocess.html",
        {"request": request, "jobs": jobs_ctx, "status": status or "all", "limit": limit},
    )


@router.get("/api/admin/postprocess_jobs")
def admin_postprocess_jobs_json(limit: int = 100, status: str = None):
    jobs = _get_jobs(limit=limit, status=status)
    now = datetime.utcnow()
    out = []
    for job in jobs:
        if job.next_attempt_at is None:
            seconds = 0
        else:
            seconds = int((job.next_attempt_at - now).total_seconds())
        def _fmt_jst(dt):
            if not dt:
                return None
            try:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if ZoneInfo is not None:
                    jst = dt.astimezone(ZoneInfo("Asia/Tokyo"))
                else:
                    jst = dt.astimezone(timezone(timedelta(hours=9)))
                return jst.strftime("%Y-%m-%d %H:%M:%S %Z")
            except Exception:
                try:
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    return None

        out.append({
            "id": job.id,
            "document_id": job.document_id,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "next_attempt_at": job.next_attempt_at.isoformat() if job.next_attempt_at else None,
            "next_attempt_at_jst": _fmt_jst(job.next_attempt_at),
            "last_error": job.last_error,
            "seconds_remaining": seconds,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "created_at_jst": _fmt_jst(job.created_at),
        })
    return {"jobs": out}
