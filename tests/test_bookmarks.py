import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_bookmark_flow(test_database_override):
    # Create a document to bookmark using the test DB URL provided by fixture
    db_url = test_database_override
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    doc = Document(
        title="Test Document",
        content_md="# Test",
        content_text="Test content",
        hash="h1"
    )
    db.add(doc)
    db.commit()
    # refresh to get generated id
    db.refresh(doc)
    doc_id = doc.id
    db.close()

    client = TestClient(app)

    # Create bookmark
    resp = client.post("/api/bookmarks", json={"document_id": doc_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc_id
    bm_id = data["id"]

    # List bookmarks
    resp2 = client.get("/api/bookmarks")
    assert resp2.status_code == 200
    l = resp2.json()
    assert any(b["id"] == bm_id for b in l["bookmarks"])

    # Delete bookmark
    resp3 = client.delete(f"/api/bookmarks/{bm_id}")
    assert resp3.status_code == 200
    assert resp3.json()["message"] == "deleted"

    # Ensure deleted
    resp4 = client.get("/api/bookmarks")
    assert resp4.status_code == 200
    assert not any(b["id"] == bm_id for b in resp4.json()["bookmarks"]) 
