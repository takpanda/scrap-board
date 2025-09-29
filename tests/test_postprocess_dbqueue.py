import os
import time
from datetime import datetime

import pytest

# Delay importing DB objects until we set DB_URL in the test function to ensure
# SessionLocal is bound to the test SQLite file.
from app.core.database import Document, Embedding, PostprocessJob, PreferenceJob


async def _fake_generate_summary(text, style="short", timeout_sec=None):
    return "自動テスト用の短い要約"


async def _fake_create_embedding(text):
    return [0.1, 0.2, 0.3]


async def _fake_classify_content(title, content):
    return {"primary_category": "テック/AI", "tags": ["AI"], "confidence": 0.9}


def test_db_queue_job_success(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    os.environ["DB_URL"] = f"sqlite:///{db_file}"

    # Now import DB helpers so we can create tables on the test DB
    from app.core.database import create_tables

    create_tables()
    # Import SessionLocal after create_tables so the sessionmaker is bound
    # to the temporary test DB created above.
    from app.core.database import SessionLocal

    import app.services.llm_client as llm_mod
    monkeypatch.setattr(llm_mod.llm_client, "generate_summary", _fake_generate_summary)
    monkeypatch.setattr(llm_mod.llm_client, "create_embedding", _fake_create_embedding)
    monkeypatch.setattr(llm_mod.llm_client, "classify_content", _fake_classify_content)

    from app.services.ingest_worker import _insert_document_if_new

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

        # Debug dump: open a fresh engine bound to DB_URL and list documents/jobs
        from sqlalchemy import create_engine, text
        db_url = os.environ.get("DB_URL")
        eng = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in (db_url or "") else {})
        with eng.connect() as conn:
            docs = conn.execute(text("SELECT id, url FROM documents")).fetchall()
            jobs = conn.execute(text("SELECT id, document_id, status FROM postprocess_jobs")).fetchall()

        # run worker loop once in the same thread (short-circuit)
        # to avoid spawning background threads in tests, import the helper and run one iteration
        from app.services.postprocess_queue import _acquire_job, _mark_job_done

        db2 = SessionLocal()
        try:
            job = _acquire_job(db2)
            assert job is not None
            # call process directly
            from app.services.postprocess import process_doc_once

            success, error = process_doc_once(job.document_id)
            assert success
            _mark_job_done(db2, job)

            # verify DB updated
            d = db2.query(Document).filter(Document.id == new_id).one_or_none()
            assert d is not None
            assert d.short_summary is not None
            emb_count = db2.query(Embedding).filter(Embedding.document_id == new_id).count()
            assert emb_count >= 1
            preference_jobs = db2.query(PreferenceJob).filter(PreferenceJob.document_id == new_id).all()
            assert len(preference_jobs) >= 1
        finally:
            db2.close()
    finally:
        db.close()
