"""Batch-enqueue profile_rebuild jobs for user 'guest'.

This script queries all document IDs and enqueues jobs in batches using
app.services.personalization_queue.enqueue_profile_update.

Usage: PYTHONPATH=. python scripts/enqueue_guest_profile_rebuild.py
"""
from __future__ import annotations

from math import ceil
from typing import List

from app.core.database import SessionLocal, Document
from app.services import personalization_queue
from app.core.user_utils import normalize_user_id

BATCH_SIZE = 200


def get_all_document_ids(session) -> List[str]:
    return [d.id for d in session.query(Document.id).all()]


def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def main():
    session = SessionLocal()
    try:
        doc_ids = get_all_document_ids(session)
        total = len(doc_ids)
        if total == 0:
            print("No documents found; nothing to enqueue")
            return
        batches = list(chunk_list(doc_ids, BATCH_SIZE))
        print(f"Enqueuing {len(batches)} jobs for {total} documents (batch size {BATCH_SIZE})")
        user = normalize_user_id("guest")
        created = 0
        for i, batch in enumerate(batches, start=1):
            payload = {"document_ids": batch}
            job_id = personalization_queue.enqueue_profile_update(session, user_id=user, payload=payload)
            print(f"  enqueued job {job_id} ({i}/{len(batches)}) docs={len(batch)}")
            created += 1
        print(f"Done: enqueued {created} jobs for user={user}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
