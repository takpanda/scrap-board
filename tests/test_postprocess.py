import os
import time
import pytest


async def _fake_generate_summary(text, style="short", timeout_sec=None):
    return "自動テスト用の短い要約"


async def _fake_create_embedding(text):
    return [0.1, 0.2, 0.3]


def test_postprocess_generates_summary_and_embedding(tmp_path, monkeypatch):
    # Use an isolated sqlite file for the test
    db_file = tmp_path / "test.db"
    os.environ["DB_URL"] = f"sqlite:///{db_file}"

    # Ensure tables are created under the test DB
    from app.core.database import create_tables, Document, Embedding, PreferenceJob

    create_tables()
    from app.core.database import SessionLocal

    # Monkeypatch LLM client methods to avoid external calls
    import app.services.llm_client as llm_mod
    monkeypatch.setattr(llm_mod.llm_client, "generate_summary", _fake_generate_summary)
    monkeypatch.setattr(llm_mod.llm_client, "create_embedding", _fake_create_embedding)

    # Insert a document via the ingest helper which will kick postprocess
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

        # Wait for DB-backed postprocess job to complete (polling). This avoids
        # relying on the legacy background thread behavior and matches the new
        # DB-backed job queue design used in production.
        from app.services.postprocess_queue import _acquire_job, _mark_job_done, _mark_job_failed

        found = False
        for _ in range(20):
            db2 = SessionLocal()
            try:
                d = db2.query(Document).filter(Document.id == new_id).one_or_none()
                if d and d.short_summary:
                    emb_count = db2.query(Embedding).filter(Embedding.document_id == new_id).count()
                    assert emb_count >= 1
                    found = True
                    break
                # try to acquire a job and process it inline to speed up tests
                job = _acquire_job(db2)
                if job:
                    success, err = __import__('app.services.postprocess', fromlist=['process_doc_once']).process_doc_once(job.document_id)
                    if success:
                        _mark_job_done(db2, job)
                    else:
                        _mark_job_failed(db2, job, err or 'err')
            finally:
                db2.close()

            time.sleep(0.25)

        if not found:
            pytest.fail("Postprocess did not generate summary/embedding in time")

        with SessionLocal() as verify:
            pref_jobs = verify.query(PreferenceJob).filter(PreferenceJob.document_id == new_id).all()
            assert len(pref_jobs) >= 1

    finally:
        db.close()
