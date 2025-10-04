import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Document


def _create_document(db, title, created_at):
    doc = Document(
        title=title,
        content_md="# test",
        content_text="test",
        hash="h-" + title,
        created_at=created_at,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.mark.usefixtures("test_database_override")
def test_api_documents_returns_created_at_desc(test_database_override):
    # Prepare DB session
    from app.core.database import SessionLocal
    db = SessionLocal()

    try:
        now = datetime.utcnow()
        d1 = _create_document(db, "a", now - timedelta(days=2))
        d2 = _create_document(db, "b", now - timedelta(days=1))
        d3 = _create_document(db, "c", now)

        with TestClient(app) as client:
            resp = client.get("/api/documents?limit=10")
            assert resp.status_code == 200
            data = resp.json()
            ids = [d["id"] for d in data["documents"]]
            # Expect c, b, a
            assert ids == [d3.id, d2.id, d1.id]
    finally:
        db.close()


@pytest.mark.usefixtures("test_database_override")
def test_documents_page_renders_in_created_at_order(test_database_override):
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        d1 = _create_document(db, "A", now - timedelta(minutes=30))
        d2 = _create_document(db, "B", now - timedelta(minutes=10))
        d3 = _create_document(db, "C", now)

        with TestClient(app) as client:
            resp = client.get("/documents")
            assert resp.status_code == 200
            html = resp.text
            # Extract data-document-id attributes only from article elements (avoid duplicate attributes elsewhere)
            import re
            ids = re.findall(r'<article[^>]*data-document-id="([^"]+)"', html)
            # First three ids should match d3, d2, d1
            assert ids[:3] == [d3.id, d2.id, d1.id]
    finally:
        db.close()
