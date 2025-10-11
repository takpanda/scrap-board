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


def test_delete_personalized_feedback_removes_record(test_database_override):
    """Test that DELETE endpoint removes feedback record."""
    session_factory = _prepare_session_factory(test_database_override)
    document_id = _create_document(session_factory)
    client = TestClient(app)

    # First, submit feedback
    post_response = client.post(
        f"/api/documents/{document_id}/personalized-feedback",
        json={"reason": "low_relevance", "session_token": "session-delete-1"},
    )
    assert post_response.status_code == 200
    assert post_response.json()["state"] == "submitted"

    # Verify feedback was created
    with session_factory() as verify:
        feedback_rows = verify.query(PreferenceFeedback).all()
        assert len(feedback_rows) == 1

    # Now delete the feedback
    delete_response = client.delete(
        f"/api/documents/{document_id}/personalized-feedback",
    )
    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["status"] == "deleted"
    assert payload["document_id"] == document_id

    # Verify feedback was deleted
    with session_factory() as verify:
        feedback_rows = verify.query(PreferenceFeedback).all()
        assert len(feedback_rows) == 0


def test_delete_personalized_feedback_missing_document_returns_404(test_database_override):
    """Test that DELETE endpoint returns 404 for non-existent document."""
    client = TestClient(app)
    response = client.delete(
        "/api/documents/does-not-exist/personalized-feedback",
    )
    assert response.status_code == 404


def test_delete_personalized_feedback_not_found_returns_404(test_database_override):
    """Test that DELETE endpoint returns 404 when no feedback exists."""
    session_factory = _prepare_session_factory(test_database_override)
    document_id = _create_document(session_factory)
    client = TestClient(app)

    # Try to delete feedback that doesn't exist
    response = client.delete(
        f"/api/documents/{document_id}/personalized-feedback",
    )
    assert response.status_code == 404


def test_delete_personalized_feedback_can_resubmit_after_deletion(test_database_override):
    """Test that feedback can be resubmitted after deletion."""
    session_factory = _prepare_session_factory(test_database_override)
    document_id = _create_document(session_factory)
    client = TestClient(app)

    # Submit feedback
    post_response = client.post(
        f"/api/documents/{document_id}/personalized-feedback",
        json={"reason": "low_relevance", "session_token": "session-resubmit"},
    )
    assert post_response.status_code == 200

    # Delete feedback
    delete_response = client.delete(
        f"/api/documents/{document_id}/personalized-feedback",
    )
    assert delete_response.status_code == 200

    # Resubmit feedback - should succeed
    repost_response = client.post(
        f"/api/documents/{document_id}/personalized-feedback",
        json={"reason": "low_relevance", "session_token": "session-resubmit-2"},
    )
    assert repost_response.status_code == 200
    assert repost_response.json()["state"] == "submitted"

    # Verify only one feedback exists
    with session_factory() as verify:
        feedback_rows = verify.query(PreferenceFeedback).all()
        assert len(feedback_rows) == 1
