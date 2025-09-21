import logging
import json
import asyncio
from threading import Thread
from datetime import datetime
from typing import Optional

from app.core.database import SessionLocal, Document, Embedding, Classification
from app.services.llm_client import llm_client
from app.services.extractor import content_extractor
from app.core.config import settings

logger = logging.getLogger(__name__)


def _process_doc_sync(doc_id: str):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).one_or_none()
        if not doc:
            logger.warning("Postprocess: document not found %s", doc_id)
            return

        text = content_extractor.prepare_text_for_summary(doc.content_text or "", max_chars=settings.short_summary_max_chars)
        if not text:
            logger.info("Postprocess: empty text for %s", doc_id)
        else:
            # Short summary
            try:
                summary = asyncio.run(llm_client.generate_summary(text, style="short", timeout_sec=settings.summary_timeout_sec))
                if summary:
                    doc.short_summary = summary[: settings.short_summary_max_chars]
                    doc.summary_generated_at = datetime.utcnow()
                    doc.summary_model = settings.summary_model or settings.chat_model
                    db.add(doc)
                    db.commit()
                    logger.info("Postprocess: saved short summary for %s", doc_id)
            except Exception as e:
                logger.error("Postprocess: summary generation failed for %s: %s", doc_id, e)

            # Embedding (single-chunk fallback)
            try:
                emb = asyncio.run(llm_client.create_embedding(text))
                if emb:
                    emb_row = Embedding(document_id=doc.id, chunk_id=0, vec=json.dumps(emb), chunk_text=text[:1000])
                    db.add(emb_row)
                    db.commit()
                    logger.info("Postprocess: saved embedding for %s", doc_id)
            except Exception as e:
                logger.error("Postprocess: embedding failed for %s: %s", doc_id, e)

            # Classification (ensure JOB-inserted docs get a category)
            try:
                classification_result = asyncio.run(llm_client.classify_content(doc.title or "", (doc.content_text or "")[:2000]))
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
                logger.error("Postprocess: classification failed for %s: %s", doc_id, e)

    except Exception:
        logger.exception("Postprocess unexpected error for %s", doc_id)
    finally:
        db.close()


def kick_postprocess_async(doc_id: str):
    """Start a background thread to generate summaries and embeddings for `doc_id`.

    This is intentionally simple: runs async LLM calls via `asyncio.run` inside a daemon
    thread so the ingest path remains non-blocking. It's best-effort and logs failures.
    """
    Thread(target=_process_doc_sync, args=(doc_id,), daemon=True).start()
