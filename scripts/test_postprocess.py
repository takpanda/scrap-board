#!/usr/bin/env python3
"""Simple local test to insert a document and observe postprocess behavior.

Usage:
  python scripts/test_postprocess.py

This script inserts a lightweight document via the same insert helper used by the ingest worker
and then waits a short time to let the background postprocess thread run.
"""
import time
from datetime import datetime
from app.core.database import SessionLocal
from app.services.ingest_worker import _insert_document_if_new


def main():
    db = SessionLocal()
    doc = {
        "url": f"http://example.com/test-{int(time.time())}",
        "domain": "example.com",
        "title": "テスト記事",
        "author": "tester",
        "published_at": datetime.utcnow().isoformat(),
        "content_md": "# テスト\n本文のサンプルです",
        "content_text": "本文のサンプルです",
        "hash": "hash-test-123",
    }

    try:
        new_id = _insert_document_if_new(db, doc, "test-source")
        print("Inserted id:", new_id)
        if new_id:
            print("Waiting 10s for postprocess to run...")
            time.sleep(10)
            # Check DB for summary/embedding
            db2 = SessionLocal()
            from app.core.database import Document, Embedding
            d = db2.query(Document).filter(Document.id == new_id).one_or_none()
            if d:
                print("short_summary:", d.short_summary)
                emb = db2.query(Embedding).filter(Embedding.document_id == new_id).all()
                print("embeddings:", len(emb))
            else:
                print("Document not found after insert")
    finally:
        db.close()


if __name__ == '__main__':
    main()
