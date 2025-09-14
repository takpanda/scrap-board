#!/usr/bin/env python3
"""Batch script to generate summaries for existing documents.

Usage examples:
  python scripts/generate_summaries_for_existing.py --limit 100
  python scripts/generate_summaries_for_existing.py --dry-run --sleep 0.5

The script iterates documents where `short_summary` is NULL and generates short summaries
using the project's LLM client. It supports dry-run, rate limiting, and resume.
"""
import argparse
import asyncio
import logging
import time
from datetime import datetime

from app.core.database import SessionLocal, Document
from app.services.extractor import content_extractor
from app.services.llm_client import llm_client
from app.core.config import settings

logger = logging.getLogger("migrate_summaries")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def generate_for_doc(doc, dry_run: bool):
    text = content_extractor.prepare_text_for_summary(doc.content_text or "", max_chars=settings.short_summary_max_chars)
    if not text:
        logger.info(f"Skipping {doc.id}: empty content")
        return False

    try:
        summary = await llm_client.generate_summary(text, style="short", timeout_sec=settings.summary_timeout_sec)
        if summary is None:
            logger.warning(f"Summary generation returned None for {doc.id}")
            return False

        if dry_run:
            logger.info(f"[dry-run] Would update {doc.id} -> {summary[:80]!r}")
            return True

        doc.short_summary = summary[: settings.short_summary_max_chars]
        doc.summary_generated_at = datetime.utcnow()
        doc.summary_model = settings.summary_model or settings.chat_model
        return True

    except Exception as e:
        logger.error(f"Error generating summary for {doc.id}: {e}")
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0, help="Max number of documents to process (0 = all)")
    p.add_argument("--batch-size", type=int, default=10, help="How many docs to fetch per DB query")
    p.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between requests (rate limit)")
    p.add_argument("--dry-run", action="store_true", help="Do not write changes to DB")
    p.add_argument("--resume", action="store_true", help="Only process documents where short_summary IS NULL")
    args = p.parse_args()

    processed = 0
    successes = 0
    failures = 0

    db = SessionLocal()
    try:
        query = db.query(Document)
        if args.resume:
            query = query.filter(Document.short_summary == None)

        total_to_process = query.count() if args.limit == 0 else min(args.limit, query.count())
        logger.info(f"Starting summary generation: target={total_to_process} (dry_run={args.dry_run})")

        offset = 0
        while True:
            q = db.query(Document)
            if args.resume:
                q = q.filter(Document.short_summary == None)
            q = q.order_by(Document.created_at.asc()).offset(offset).limit(args.batch_size)
            docs = q.all()
            if not docs:
                break

            for doc in docs:
                if args.limit and processed >= args.limit:
                    break

                success = asyncio.run(generate_for_doc(doc, args.dry_run))
                processed += 1
                if success:
                    successes += 1
                    if not args.dry_run:
                        try:
                            db.add(doc)
                            db.commit()
                        except Exception as e:
                            logger.error(f"DB commit failed for {doc.id}: {e}")
                            db.rollback()
                            failures += 1
                else:
                    failures += 1

                time.sleep(args.sleep)

            if args.limit and processed >= args.limit:
                break

            offset += args.batch_size

        logger.info(f"Completed: processed={processed} successes={successes} failures={failures}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
