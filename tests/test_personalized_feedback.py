from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Document, PreferenceFeedback, PreferenceJob


def _prepare_session_factory(db_url: str):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_document(session_factory) -> str:
    session = session_factory()
    try:
        document = Document(
            title="Test Personalized Feedback Document",
            content_md="# test",
            content_text="body",
            hash="hash-personalized-feedback-" + uuid4().hex,
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        return document.id
    finally:
        session.close()


def test_personalized_feedback_creates_record_and_job(test_database_override):
    session_factory = _prepare_session_factory(test_database_override)
    document_id = _create_document(session_factory)
    client = TestClient(app)

    response = client.post(
        f"/api/documents/{document_id}/personalized-feedback",
        json={"reason": "low_relevance", "session_token": "session-a"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["state"] == "submitted"
    assert payload["duplicate"] is False
    assert payload["document_id"] == document_id

    with session_factory() as verify:
        feedback_rows = verify.query(PreferenceFeedback).all()
        assert len(feedback_rows) == 1
        assert feedback_rows[0].document_id == document_id
        assert feedback_rows[0].feedback_type == "low_relevance"

        job_rows = verify.query(PreferenceJob).all()
        assert len(job_rows) == 1
        assert job_rows[0].document_id == document_id


def test_personalized_feedback_duplicate_session(test_database_override):
    session_factory = _prepare_session_factory(test_database_override)
    document_id = _create_document(session_factory)
    client = TestClient(app)

    first = client.post(
        f"/api/documents/{document_id}/personalized-feedback",
        json={"reason": "low_relevance", "session_token": "session-b"},
    )
    assert first.status_code == 200
    assert first.json()["state"] == "submitted"

    second = client.post(
        f"/api/documents/{document_id}/personalized-feedback",
        json={"reason": "low_relevance", "session_token": "session-b"},
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "duplicate"
    assert payload["state"] == "duplicate"
    assert payload["duplicate"] is True

    with session_factory() as verify:
        feedback_rows = list(verify.query(PreferenceFeedback).all())
        assert len(feedback_rows) == 1, [
            (row.document_id, row.metadata_payload, row.user_id) for row in feedback_rows
        ]
        assert verify.query(PreferenceJob).count() == 1


def test_personalized_feedback_missing_document_returns_404(test_database_override):
    client = TestClient(app)
    response = client.post(
        "/api/documents/does-not-exist/personalized-feedback",
        json={"reason": "low_relevance", "session_token": "session-c"},
    )
    assert response.status_code == 404


def test_personalized_feedback_rejects_unknown_reason(test_database_override):
    session_factory = _prepare_session_factory(test_database_override)
    document_id = _create_document(session_factory)
    client = TestClient(app)

    response = client.post(
        f"/api/documents/{document_id}/personalized-feedback",
        json={"reason": "thumbs_up", "session_token": "session-d"},
    )
    assert response.status_code == 400
