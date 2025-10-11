"""Tests for guest user functionality across bookmarks and feedback."""
import pytest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Document, Bookmark, PreferenceFeedback, PersonalizedScore
from app.core.user_utils import GUEST_USER_ID, normalize_user_id


def _prepare_session(db_url: str):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def _clear_tables(db):
    db.query(PersonalizedScore).delete()
    db.query(PreferenceFeedback).delete()
    db.query(Bookmark).delete()
    db.query(Document).delete()
    db.commit()


def _create_document(db, *, title: str, created_at: datetime):
    doc = Document(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-').lower()}",
        content_md="# Sample",
        content_text="Sample content",
        hash=f"hash-{title.replace(' ', '-').lower()}"
    )
    doc.created_at = created_at
    doc.updated_at = created_at
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def test_normalize_user_id_none_returns_guest():
    """Test that normalize_user_id converts None to 'guest'."""
    assert normalize_user_id(None) == GUEST_USER_ID


def test_normalize_user_id_empty_string_returns_guest():
    """Test that normalize_user_id converts empty string to 'guest'."""
    assert normalize_user_id("") == GUEST_USER_ID
    assert normalize_user_id("   ") == GUEST_USER_ID


def test_normalize_user_id_preserves_valid_id():
    """Test that normalize_user_id preserves valid user IDs."""
    assert normalize_user_id("user-123") == "user-123"
    assert normalize_user_id("alice") == "alice"


def test_bookmark_create_without_user_header_uses_guest(test_database_override):
    """Test that creating a bookmark without a user header uses 'guest' user_id."""
    db = _prepare_session(test_database_override)
    _clear_tables(db)
    
    created = datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc)
    doc = _create_document(db, title="Test Article", created_at=created)
    db.close()
    
    client = TestClient(app)
    # No X-User-Id header = guest user
    response = client.post("/api/bookmarks", json={"document_id": doc.id})
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    
    # Verify in database
    db = _prepare_session(test_database_override)
    bookmark = db.query(Bookmark).filter(Bookmark.document_id == doc.id).first()
    assert bookmark is not None
    assert bookmark.user_id == GUEST_USER_ID
    db.close()


def test_bookmark_list_without_user_header_returns_guest_bookmarks(test_database_override):
    """Test that listing bookmarks without user header returns guest bookmarks."""
    db = _prepare_session(test_database_override)
    _clear_tables(db)
    
    created = datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc)
    doc = _create_document(db, title="Guest Article", created_at=created)
    doc_id = doc.id  # Capture ID before closing session
    
    # Create a guest bookmark
    bookmark = Bookmark(
        user_id=GUEST_USER_ID,
        document_id=doc.id,
        note="Guest note"
    )
    db.add(bookmark)
    db.commit()
    db.close()
    
    client = TestClient(app)
    response = client.get("/api/bookmarks")
    
    assert response.status_code == 200
    data = response.json()
    assert "bookmarks" in data
    assert len(data["bookmarks"]) == 1
    assert data["bookmarks"][0]["document_id"] == doc_id


def test_bookmark_duplicate_prevention_for_guest(test_database_override):
    """Test that duplicate bookmarks are prevented for guest user."""
    db = _prepare_session(test_database_override)
    _clear_tables(db)
    
    created = datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc)
    doc = _create_document(db, title="Duplicate Test", created_at=created)
    db.close()
    
    client = TestClient(app)
    
    # First bookmark
    response1 = client.post("/api/bookmarks", json={"document_id": doc.id})
    assert response1.status_code == 200
    bookmark1_id = response1.json()["id"]
    
    # Second attempt should return the same bookmark
    response2 = client.post("/api/bookmarks", json={"document_id": doc.id})
    assert response2.status_code == 200
    bookmark2_id = response2.json()["id"]
    
    assert bookmark1_id == bookmark2_id
    
    # Verify only one bookmark exists
    db = _prepare_session(test_database_override)
    count = db.query(Bookmark).filter(
        Bookmark.user_id == GUEST_USER_ID,
        Bookmark.document_id == doc.id
    ).count()
    assert count == 1
    db.close()


def test_guest_and_authenticated_bookmarks_are_separate(test_database_override):
    """Test that guest and authenticated user bookmarks are kept separate."""
    db = _prepare_session(test_database_override)
    _clear_tables(db)
    
    created = datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc)
    doc = _create_document(db, title="Shared Article", created_at=created)
    doc_id = doc.id  # Capture ID before closing session
    db.close()
    
    client = TestClient(app)
    
    # Guest user bookmarks the document
    response1 = client.post("/api/bookmarks", json={"document_id": doc_id})
    assert response1.status_code == 200
    
    # Authenticated user bookmarks the same document
    response2 = client.post(
        "/api/bookmarks",
        json={"document_id": doc_id},
        headers={"X-User-Id": "alice"}
    )
    assert response2.status_code == 200
    
    # Verify two separate bookmarks exist
    db = _prepare_session(test_database_override)
    guest_bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == GUEST_USER_ID,
        Bookmark.document_id == doc_id
    ).first()
    alice_bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == "alice",
        Bookmark.document_id == doc_id
    ).first()
    
    assert guest_bookmark is not None
    assert alice_bookmark is not None
    assert guest_bookmark.id != alice_bookmark.id
    db.close()


def test_bookmarks_page_without_header_shows_guest_bookmarks(test_database_override):
    """Test that the bookmarks page without user header shows guest bookmarks."""
    db = _prepare_session(test_database_override)
    _clear_tables(db)
    
    created = datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc)
    doc = _create_document(db, title="Guest Page Article", created_at=created)
    
    # Create a guest bookmark
    bookmark = Bookmark(
        user_id=GUEST_USER_ID,
        document_id=doc.id,
        note="Guest page note"
    )
    db.add(bookmark)
    db.commit()
    db.close()
    
    client = TestClient(app)
    response = client.get("/bookmarks")
    
    assert response.status_code == 200
    assert "Guest Page Article" in response.text
    assert "Guest page note" in response.text


def test_feedback_without_user_uses_guest(test_database_override):
    """Test that submitting feedback without user ID uses 'guest'."""
    db = _prepare_session(test_database_override)
    _clear_tables(db)
    
    created = datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc)
    doc = _create_document(db, title="Feedback Test", created_at=created)
    doc_id = doc.id  # Capture ID before closing session
    db.close()
    
    client = TestClient(app)
    
    # Submit feedback without user header
    response = client.post(
        f"/api/documents/{doc_id}/personalized-feedback",
        json={"reason": "low_relevance", "note": "Not relevant"}
    )
    
    assert response.status_code == 200
    
    # Verify feedback was saved with guest user_id
    db = _prepare_session(test_database_override)
    feedback = db.query(PreferenceFeedback).filter(
        PreferenceFeedback.document_id == doc_id
    ).first()
    assert feedback is not None
    assert feedback.user_id == GUEST_USER_ID
    db.close()


def test_feedback_duplicate_prevention_for_guest(test_database_override):
    """Test that duplicate feedback is prevented for guest user."""
    db = _prepare_session(test_database_override)
    _clear_tables(db)
    
    created = datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc)
    doc = _create_document(db, title="Duplicate Feedback Test", created_at=created)
    doc_id = doc.id  # Capture ID before closing session
    db.close()
    
    client = TestClient(app)
    
    # First feedback
    response1 = client.post(
        f"/api/documents/{doc_id}/personalized-feedback",
        json={"reason": "low_relevance", "note": "First feedback", "session_token": "guest-session-1"}
    )
    assert response1.status_code == 200
    result1 = response1.json()
    # The API returns "state" field, not "created"
    assert result1.get("state") == "submitted"
    
    # Second attempt should be rejected as duplicate
    response2 = client.post(
        f"/api/documents/{doc_id}/personalized-feedback",
        json={"reason": "low_relevance", "note": "Second feedback", "session_token": "guest-session-1"}
    )
    assert response2.status_code == 200
    result2 = response2.json()
    # The API returns "state" = "duplicate" for duplicates, not "created" = False
    assert result2.get("status") == "duplicate"
    assert result2.get("state") == "duplicate"
