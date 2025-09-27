from fastapi.testclient import TestClient
from app.main import app


def test_bookmarks_page_returns_200():
    client = TestClient(app)
    res = client.get("/bookmarks")
    assert res.status_code == 200
    assert "ブックマーク" in res.text
