from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Document, Bookmark


def _prepare_session(db_url: str):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def _clear_tables(db):
    db.query(Bookmark).delete()
    db.query(Document).delete()
    db.commit()


def _create_bookmark(db, *, title: str, user_id: str | None, created_at: datetime, note: str):
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
    db.flush()

    bookmark = Bookmark(
        user_id=user_id,
        document_id=doc.id,
        note=note,
        created_at=created_at
    )
    db.add(bookmark)
    db.commit()
    db.refresh(doc)
    return doc, bookmark


def test_bookmarks_page_filters_by_user(test_database_override):
    db = _prepare_session(test_database_override)
    _clear_tables(db)

    created = datetime(2025, 9, 27, 12, 30, tzinfo=timezone.utc)
    doc_user_a, _ = _create_bookmark(db, title="User A Article", user_id="user-a", created_at=created, note="気になる記事")
    _create_bookmark(db, title="User B Article", user_id="user-b", created_at=created + timedelta(hours=1), note="別ユーザー")
    db.close()

    client = TestClient(app)
    res = client.get("/bookmarks", headers={"X-User-Id": "user-a"})

    assert res.status_code == 200
    body = res.text
    assert "User A Article" in body
    assert "User B Article" not in body
    assert "気になる記事" in body
    assert "表示範囲: 1 - 1 / 1" in body


def test_bookmarks_page_shows_empty_state(test_database_override):
    db = _prepare_session(test_database_override)
    _clear_tables(db)
    db.close()

    client = TestClient(app)
    res = client.get("/bookmarks", headers={"X-User-Id": "user-z"})

    assert res.status_code == 200
    assert "ブックマークした記事はありません" in res.text


def test_bookmarks_page_clamps_to_last_page(test_database_override):
    db = _prepare_session(test_database_override)
    _clear_tables(db)

    created = datetime(2025, 9, 27, 9, 0, tzinfo=timezone.utc)
    titles = ["記事1", "記事2", "記事3"]
    for idx, title in enumerate(titles):
        _create_bookmark(
            db,
            title=title,
            user_id="user-a",
            created_at=created + timedelta(hours=idx),
            note=f"メモ{idx + 1}"
        )
    db.close()

    client = TestClient(app)
    res = client.get("/bookmarks?per_page=1&page=5", headers={"X-User-Id": "user-a"})

    assert res.status_code == 200
    body = res.text
    # Last page should clamp to the oldest bookmark (記事1)
    assert "記事1" in body
    assert "メモ1" in body
    assert "表示範囲: 3 - 3 / 3" in body
