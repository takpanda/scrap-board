import os
import time
from datetime import datetime

import pytest

from app.core.database import Document


class DummyFailOnce:
    def __init__(self):
        self.called = 0

    async def __call__(self, *args, **kwargs):
        self.called += 1
        if self.called == 1:
            raise RuntimeError("simulated transient failure")
        return "回復後の要約"


async def _fake_create_embedding(text):
    return [0.1, 0.2, 0.3]


async def _fake_classify_content(title, content):
    return {"primary_category": "テック/AI", "tags": ["AI"], "confidence": 0.9}


def test_db_queue_job_retry(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    os.environ["DB_URL"] = f"sqlite:///{db_file}"

    

    from app.core.database import create_tables

    create_tables()
    from app.core.database import SessionLocal

    fail_once = DummyFailOnce()

    import app.services.llm_client as llm_mod
    monkeypatch.setattr(llm_mod.llm_client, "generate_summary", fail_once)
    monkeypatch.setattr(llm_mod.llm_client, "create_embedding", _fake_create_embedding)
    monkeypatch.setattr(llm_mod.llm_client, "classify_content", _fake_classify_content)

    from app.services.ingest_worker import _insert_document_if_new
    from app.services.postprocess_queue import enqueue_job_for_document, _acquire_job, _mark_job_done, _mark_job_failed
    from app.services.postprocess import process_doc_once

    db = SessionLocal()
    try:
        doc = {
            "url": f"http://example.test/post-{int(time.time())}",
            "domain": "example.test",
            "title": "テスト記事",
            "author": "pytest",
            "published_at": None,
            "content_md": "# テスト\nこれはテストです",
            "content_text": "これはテストです",
            "hash": f"hash-{int(time.time())}",
        }

        new_id = _insert_document_if_new(db, doc, "test-source")
        assert new_id is not None

        # acquire job and run first attempt (should fail)
        db2 = SessionLocal()
        try:
            job = _acquire_job(db2)
            assert job is not None
            success, error = process_doc_once(job.document_id)
            assert not success
            _mark_job_failed(db2, job, error or "err")

            # simulate waiting until next_attempt_at
            job2 = db2.query(type(job)).filter(type(job).id == job.id).one()
            assert job2.status == "pending"

            # fast-forward next attempt by clearing next_attempt_at
            job2.next_attempt_at = None
            db2.add(job2)
            db2.commit()

            # acquire again and succeed
            job3 = _acquire_job(db2)
            assert job3 is not None
            success2, err2 = process_doc_once(job3.document_id)
            assert success2
            _mark_job_done(db2, job3)

            d = db2.query(Document).filter(Document.id == new_id).one_or_none()
            assert d is not None and d.short_summary is not None
        finally:
            db2.close()
    finally:
        db.close()
