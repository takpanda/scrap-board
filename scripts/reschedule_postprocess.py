#!/usr/bin/env python3
"""Reschedule postprocess jobs for documents missing summaries or classifications.

Usage:
  python scripts/reschedule_postprocess.py --dry-run --limit 10

By default the script lists affected document IDs. Without `--dry-run` it will
create rows in the `postprocess_jobs` table using the project's enqueue helper.
"""
import argparse
import logging
from typing import List

from app.core.database import SessionLocal, Document, Classification
from app.services.postprocess_queue import enqueue_job_for_document


logger = logging.getLogger("reschedule")


def find_missing(db, only_summaries: bool, only_classifications: bool) -> List[str]:
    ids = set()

    if not only_classifications:
        rows = db.query(Document.id).filter(Document.short_summary == None).all()
        ids.update([r[0] if isinstance(r, tuple) else r.id for r in rows])

    if not only_summaries:
        # Left outer join to find documents without any classification rows
        rows = (
            db.query(Document.id)
            .outerjoin(Classification, Classification.document_id == Document.id)
            .filter(Classification.id == None)
            .all()
        )
        ids.update([r[0] if isinstance(r, tuple) else r.id for r in rows])

    return list(ids)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0, help="Max number of documents to process (0 = all)")
    p.add_argument("--dry-run", action="store_true", help="Only show what would be enqueued")
    p.add_argument("--only-summaries", action="store_true", help="Target only documents missing summaries")
    p.add_argument("--only-classifications", action="store_true", help="Target only documents missing classifications")
    args = p.parse_args()

    db = SessionLocal()
    try:
        ids = find_missing(db, only_summaries=args.only_summaries, only_classifications=args.only_classifications)
        total = len(ids)
        if args.limit and args.limit > 0:
            ids = ids[: args.limit]

        if not ids:
            print("No documents found that match the criteria.")
            return

        print(f"Found {total} documents; will process {len(ids)} (dry-run={args.dry_run})")
        print("Sample IDs:")
        for doc_id in ids[:10]:
            print(" -", doc_id)

        if args.dry_run:
            print("Dry-run mode: not enqueuing jobs.")
            return

        # Enqueue jobs
        for doc_id in ids:
            try:
                job_id = enqueue_job_for_document(db, doc_id)
                print(f"Enqueued job {job_id} for document {doc_id}")
            except Exception as e:
                logger.exception("Failed to enqueue for %s: %s", doc_id, e)

    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
