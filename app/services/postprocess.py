import logging
import json
import asyncio
from threading import Thread
from datetime import datetime
from typing import Optional

from app.core.database import Document, Embedding, Classification, PostprocessJob
from app.services.llm_client import llm_client
from app.services.extractor import content_extractor
from app.core.config import settings
from app.services.personalization_queue import schedule_profile_update

logger = logging.getLogger(__name__)


def process_doc_once(doc_id: str):
    """Process the document once and return (success: bool, error: Optional[str]).

    This function is intended to be called by a worker that implements retry/backoff.
    """
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create a session that is explicitly bound to the current DB_URL so
    # tests which rebind module-level engines (via create_tables) don't cause
    # process_doc_once to use a stale SessionLocal with the wrong DB.
    db_url = os.environ.get("DB_URL") or settings.db_url
    create_engine_kwargs = {"connect_args": {"check_same_thread": False}} if "sqlite" in db_url else {}
    engine = create_engine(db_url, **create_engine_kwargs)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        # Debugging: use module-level engine to inspect URL
        from app.core import database as _db_mod
        try:
            engine_url = str(_db_mod.engine.url) if getattr(_db_mod, 'engine', None) and getattr(_db_mod.engine, 'url', None) else None
        except Exception:
            engine_url = None
        logger.debug("Postprocess: module.engine_url=%s", engine_url)
    except Exception:
        pass
    try:
        doc = db.query(Document).filter(Document.id == doc_id).one_or_none()
        if not doc:
            msg = f"document not found {doc_id}"
            logger.warning("Postprocess: %s", msg)
            return False, msg

        text = content_extractor.prepare_text_for_summary(doc.content_text or "", max_chars=settings.short_summary_max_chars)
        if not text:
            msg = "empty text"
            logger.info("Postprocess: %s for %s", msg, doc_id)
            return True, None

        # Short summary
        def _run_async(coro_factory):
            """Run an async coroutine produced by `coro_factory` safely.

            `coro_factory` may be either a coroutine function call (callable that
            returns a coroutine) or a coroutine object. When the current thread
            already has a running event loop (pytest/asyncio plugin), create
            the coroutine inside a new thread and execute it with
            `asyncio.run()` there to avoid cross-loop coroutine issues.
            """
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            # Helper to obtain a fresh coroutine object inside the current
            # context: if coro_factory is already a coroutine object, return
            # it; if it's callable, call it to get the coroutine.
            def _make_coro():
                if asyncio.iscoroutine(coro_factory):
                    return coro_factory
                if callable(coro_factory):
                    return coro_factory()
                raise TypeError("coro_factory must be a coroutine or callable returning a coroutine")

            # If there's a running loop in this thread, execute in a separate
            # thread and create the coroutine inside that thread.
            if loop and loop.is_running():
                result_container = {}

                def _runner():
                    try:
                        coro = _make_coro()
                        result_container["res"] = asyncio.run(coro)
                    except Exception as e:
                        result_container["exc"] = e

                t = Thread(target=_runner, daemon=True)
                t.start()
                t.join()
                if "exc" in result_container:
                    raise result_container["exc"]
                return result_container.get("res")

            # No running loop here; safe to create coroutine in this thread
            coro = _make_coro()
            return asyncio.run(coro)

        try:
            summary = _run_async(lambda: llm_client.generate_summary(text, style="short", timeout_sec=settings.summary_timeout_sec))
            if summary:
                doc.short_summary = summary[: settings.short_summary_max_chars]
                doc.summary_generated_at = datetime.utcnow()
                doc.summary_model = settings.summary_model or settings.chat_model
                db.add(doc)
                db.commit()
                logger.info("Postprocess: saved short summary for %s", doc_id)
        except Exception as e:
            logger.exception("Postprocess: summary generation failed for %s", doc_id)
            return False, f"summary error: {e}"

        # Embedding (single-chunk fallback)
        try:
            emb = _run_async(lambda: llm_client.create_embedding(text))
            if emb:
                emb_row = Embedding(document_id=doc.id, chunk_id=0, vec=json.dumps(emb), chunk_text=text[:1000])
                db.add(emb_row)
                db.commit()
                logger.info("Postprocess: saved embedding for %s", doc_id)
        except Exception as e:
            logger.exception("Postprocess: embedding failed for %s", doc_id)
            return False, f"embedding error: {e}"

        # Classification (ensure JOB-inserted docs get a category)
        try:
            classification_result = _run_async(lambda: llm_client.classify_content(doc.title or "", (doc.content_text or "")[:2000]))
            if classification_result:
                cls = Classification(
                    document_id=doc.id,
                    primary_category=classification_result.get("primary_category", "その他"),
                    topics=None,
                    tags=classification_result.get("tags", []),
                    confidence=classification_result.get("confidence", 0.5),
                    method="llm"
                )
                db.add(cls)
                db.commit()
                logger.info("Postprocess: saved classification for %s", doc_id)
        except Exception as e:
            logger.exception("Postprocess: classification failed for %s", doc_id)
            return False, f"classification error: {e}"

        job_id = schedule_profile_update(db, document_id=doc.id)
        if job_id:
            logger.debug("Postprocess: scheduled preference job %s for document %s", job_id, doc.id)

        return True, None
    except Exception:
        logger.exception("Postprocess unexpected error for %s", doc_id)
        return False, "unexpected error"
    finally:
        db.close()


def kick_postprocess_async(doc_id: str):
    """Backward-compatible helper: keep the old behavior (daemon thread, best-effort).

    Returns immediately.
    """
    Thread(target=lambda: process_doc_once(doc_id), args=(), daemon=True).start()
