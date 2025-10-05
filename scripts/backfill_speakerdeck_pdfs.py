#!/usr/bin/env python3
"""
Backfill SpeakerDeck PDFs for documents missing `pdf_path`.

Usage:
  python scripts/backfill_speakerdeck_pdfs.py       # dry-run, list candidates and found PDF URLs
  python scripts/backfill_speakerdeck_pdfs.py --apply  # actually download PDFs and update DB

This script is cautious by default (dry-run). Use --apply to perform downloads and DB updates.
"""
import argparse
import logging
from sqlalchemy import text
from app.core.database import SessionLocal
from app.services.speakerdeck_handler import SpeakerDeckHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_speakerdeck_pdfs")


def find_candidates(session):
    sql = text("""
    SELECT id, url, title FROM documents
    WHERE domain LIKE '%speakerdeck%'
      AND (pdf_path IS NULL OR trim(pdf_path) = '')
    ORDER BY created_at DESC
    """)
    return session.execute(sql).fetchall()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually download PDFs and update DB")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds for downloads")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        rows = find_candidates(session)
        if not rows:
            logger.info("No SpeakerDeck documents without pdf_path found.")
            return

        handler = SpeakerDeckHandler(timeout=args.timeout)

        to_update = []
        for r in rows:
            doc_id, url, title = r[0], r[1], r[2]
            logger.info(f"Checking document {doc_id} - {title}")
            if not url:
                logger.info("  no URL, skipping")
                continue

            pdf_url = handler.get_pdf_url(url)
            if not pdf_url:
                logger.info("  no PDF URL found")
                continue

            logger.info(f"  found PDF URL: {pdf_url}")
            to_update.append((doc_id, url, title, pdf_url))

        if not to_update:
            logger.info("No PDF URLs could be extracted for any candidate (dry-run complete).")
            return

        logger.info(f"Found {len(to_update)} documents with PDF URLs.")
        if not args.apply:
            logger.info("Dry-run mode: pass --apply to download PDFs and update the database.")
            for doc_id, url, title, pdf_url in to_update:
                print(f"{doc_id}\t{title}\t{pdf_url}")
            return

        # Apply downloads and DB updates
        for doc_id, url, title, pdf_url in to_update:
            logger.info(f"Downloading for document {doc_id} - {title}")
            rel_path = handler.download_pdf(pdf_url, doc_id)
            if not rel_path:
                logger.warning(f"  download failed for {doc_id}")
                continue

            # Update DB
            try:
                session.execute(text("UPDATE documents SET pdf_path = :p WHERE id = :id"), {"p": rel_path, "id": doc_id})
                session.commit()
                logger.info(f"  updated document {doc_id} with pdf_path={rel_path}")
            except Exception as e:
                session.rollback()
                logger.error(f"  failed to update DB for {doc_id}: {e}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
