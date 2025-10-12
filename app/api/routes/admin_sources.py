from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import json
from urllib.parse import urlparse
from sqlalchemy import text
from app.core.database import get_db
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/sources", tags=["admin-sources"])

templates = Jinja2Templates(directory="app/templates")


def _reload_scheduler_if_available():
    """Safely reload scheduler if not in test mode."""
    # Skip scheduler reload during tests
    if os.environ.get("PYTEST_CURRENT_TEST"):
        logger.debug("Test mode detected; skipping scheduler reload")
        return
    
    try:
        from app.services import scheduler
        scheduler.reload_sources()
    except Exception:
        logger.exception("Failed to reload scheduler after source change")


class SourceCreate(BaseModel):
    name: str
    type: str
    config: Optional[dict] = None
    enabled: Optional[bool] = True
    cron_schedule: Optional[str] = None


@router.get("/")
async def list_sources(request: Request, db=Depends(get_db)):
    """JSONで一覧を返すか、`?html=1` または Accept: text/html の場合は部分テンプレートを返す"""
    result = db.execute(text("SELECT id,name,type,config,enabled,cron_schedule,last_fetched_at FROM sources"))
    rows = result.fetchall()
    sources = [dict(r._mapping) for r in rows]
    # expose parsed config as dict for templates
    for s in sources:
        try:
            s["config_map"] = json.loads(s.get("config") or "{}")
        except Exception:
            s["config_map"] = {}

    # HTML 希望なら部分テンプレートを返す（HTMX 用）
    if request.query_params.get("html") == "1" or request.headers.get("accept", "").find("text/html") != -1:
        return templates.TemplateResponse("admin/_sources_list.html", {"request": request, "sources": sources})

    return sources


def _is_valid_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


@router.post("/")
async def create_source(request: Request, db=Depends(get_db)):
    """Create source. Accepts JSON or form-encoded data. Returns JSON or HTML fragment when requested."""
    content_type = request.headers.get("content-type", "")
    name = None
    type_ = None
    config = {}
    enabled = 1
    cron = None

    try:
        if "application/json" in content_type:
            payload = await request.json()
            name = payload.get("name")
            type_ = payload.get("type")
            config = payload.get("config") or {}
            # support top-level url to be merged into config
            url = payload.get("url")
            if url:
                try:
                    config = dict(config or {})
                    config["url"] = url
                except Exception:
                    pass
            enabled = int(bool(payload.get("enabled", True)))
            cron = payload.get("cron_schedule")
        else:
            form = await request.form()
            name = form.get("name")
            type_ = form.get("type")
            config_raw = form.get("config")
            url = form.get("url")
            try:
                config = json.loads(config_raw) if config_raw else {}
            except Exception:
                config = {}
            
            # Handle SpeakerDeck specific fields
            if type_ == "speakerdeck":
                username = form.get("speakerdeck_username")
                format_ = form.get("speakerdeck_format") or "rss"
                if username:
                    # Generate SpeakerDeck feed URL from username
                    url = f"https://speakerdeck.com/{username}.{format_}"
                    config["username"] = username
                    config["format"] = format_
            
            if url:
                try:
                    config = dict(config or {})
                    config["url"] = url
                except Exception:
                    pass
            enabled = 1 if form.get("enabled") in ("1", "true", "on", True) else 0
            cron = form.get("cron_schedule")
    except Exception:
        # Fallback
        payload = await request.json()
        name = payload.get("name")
        type_ = payload.get("type")
        config = payload.get("config") or {}
        enabled = int(bool(payload.get("enabled", True)))
        cron = payload.get("cron_schedule")
    # Validate URL in config if present
    try:
        url_val = config.get("url") if isinstance(config, dict) else None
    except Exception:
        url_val = None
    if url_val:
        if not _is_valid_url(url_val):
            raise HTTPException(status_code=400, detail="invalid url")
    db.execute(
        text("INSERT INTO sources (name,type,config,enabled,cron_schedule) VALUES (:name,:type,:config,:enabled,:cron)"),
        {
            "name": name,
            "type": type_,
            "config": json.dumps(config or {}),
            "enabled": int(enabled),
            "cron": cron,
        },
    )
    db.commit()

    # Reload scheduler to immediately reflect the new source
    _reload_scheduler_if_available()

    # Get last insert id (SQLite compatible)
    try:
        last_id = db.execute(text("SELECT last_insert_rowid()"))
        scalar = last_id.scalar()
    except Exception:
        scalar = None

    # If HTML requested, return updated list fragment
    if request.query_params.get("html") == "1" or request.headers.get("accept", "").find("text/html") != -1:
        return await list_sources(request, db)

    return {"id": scalar}



@router.put("/{source_id}")
async def update_source(source_id: int, request: Request, db=Depends(get_db)):
    """Update source. Accepts JSON or form-encoded data. Returns JSON or HTML fragment when requested."""
    content_type = request.headers.get("content-type", "")
    name = None
    type_ = None
    config = {}
    enabled = 1
    cron = None

    try:
        if "application/json" in content_type:
            payload = await request.json()
            name = payload.get("name")
            type_ = payload.get("type")
            config = payload.get("config") or {}
            url = payload.get("url")
            if url:
                try:
                    config = dict(config or {})
                    config["url"] = url
                except Exception:
                    pass
            enabled = int(bool(payload.get("enabled", True)))
            cron = payload.get("cron_schedule")
        else:
            form = await request.form()
            name = form.get("name")
            type_ = form.get("type")
            config_raw = form.get("config")
            url = form.get("url")
            try:
                config = json.loads(config_raw) if config_raw else {}
            except Exception:
                config = {}
            if url:
                try:
                    config = dict(config or {})
                    config["url"] = url
                except Exception:
                    pass
            enabled = 1 if form.get("enabled") in ("1", "true", "on", True) else 0
            cron = form.get("cron_schedule")
    except Exception:
        payload = await request.json()
        name = payload.get("name")
        type_ = payload.get("type")
        config = payload.get("config") or {}
        enabled = int(bool(payload.get("enabled", True)))
        cron = payload.get("cron_schedule")

    # If some fields are missing (e.g. enabled only), preserve existing values
    existing = db.execute(text("SELECT name,type,config,enabled,cron_schedule FROM sources WHERE id=:id"), {"id": source_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="source not found")
    existing_map = dict(existing._mapping)

    if name is None:
        name = existing_map.get("name")
    if type_ is None:
        type_ = existing_map.get("type")
    if config in (None, {}):
        try:
            config = json.loads(existing_map.get("config") or "{}")
        except Exception:
            config = {}
    # If a separate url was provided, prioritize it (keeps backward compatibility)
    # Note: earlier parsing attempted to merge url into config when present
    if cron is None:
        cron = existing_map.get("cron_schedule")
    if enabled in (None, ''):
        enabled = existing_map.get("enabled")

    # Validate URL in config if present before saving
    try:
        url_val = config.get("url") if isinstance(config, dict) else None
    except Exception:
        url_val = None
    if url_val:
        if not _is_valid_url(url_val):
            raise HTTPException(status_code=400, detail="invalid url")

    result = db.execute(
        text("UPDATE sources SET name=:name,type=:type,config=:config,enabled=:enabled,cron_schedule=:cron WHERE id=:id"),
        {
            "name": name,
            "type": type_,
            "config": json.dumps(config or {}),
            "enabled": int(enabled),
            "cron": cron,
            "id": source_id,
        },
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="source not found")

    # Reload scheduler to immediately reflect the updated source
    _reload_scheduler_if_available()

    if request.query_params.get("html") == "1" or request.headers.get("accept", "").find("text/html") != -1:
        return await list_sources(request, db)

    return {"updated": result.rowcount}


@router.delete("/{source_id}")
async def delete_source(source_id: int, request: Request, db=Depends(get_db)):
    result = db.execute(text("DELETE FROM sources WHERE id=:id"), {"id": source_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="source not found")

    # Reload scheduler to immediately remove the deleted source's job
    _reload_scheduler_if_available()

    if request.query_params.get("html") == "1" or request.headers.get("accept", "").find("text/html") != -1:
        return await list_sources(request, db)

    return {"deleted": result.rowcount}
