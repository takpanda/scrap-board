"""
モーダルAPIエンドポイントのテスト
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import Document, Bookmark, Classification, create_tables
from app.core import database as app_db
from datetime import datetime, timezone


@pytest.fixture()
def client():
    """TestClientのフィクスチャ"""
    create_tables()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    """DBセッションのフィクスチャ"""
    create_tables()
    session = app_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db_with_document(db_session: Session):
    """テスト用の記事データを作成"""
    # テスト用の記事を作成
    document = Document(
        id="test-doc-123",
        title="テスト記事",
        url="https://example.com/test",
        domain="example.com",
        content_md="# テスト記事\n\nこれはテストです。",
        content_text="テスト記事\n\nこれはテストです。",
        short_summary="テスト記事の要約",
        hash="test-hash-123",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc)
    )
    db_session.add(document)

    # 分類情報を追加
    classification = Classification(
        document_id="test-doc-123",
        primary_category="テスト",
        topics=["テスト"],
        tags=["pytest", "testing"],
        confidence=0.9,
        method="manual"
    )
    db_session.add(classification)

    db_session.commit()
    db_session.refresh(document)

    yield db_session

    # クリーンアップ
    db_session.query(Classification).filter(Classification.document_id == "test-doc-123").delete()
    db_session.query(Document).filter(Document.id == "test-doc-123").delete()
    db_session.commit()


def test_get_document_modal_success(client: TestClient, db_with_document: Session):
    """正常系: モーダルコンテンツの取得"""
    doc_id = "test-doc-123"
    response = client.get(f"/api/documents/{doc_id}/modal")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert doc_id in response.text or "テスト記事" in response.text


def test_get_document_modal_not_found(client: TestClient, db_session: Session):
    """異常系: 存在しない記事ID"""
    response = client.get("/api/documents/nonexistent/modal")
    assert response.status_code == 404


def test_get_document_modal_with_bookmark(client: TestClient, db_with_document: Session):
    """正常系: ブックマーク済み記事のモーダル表示"""
    doc_id = "test-doc-123"

    # ブックマークを追加
    bookmark = Bookmark(
        document_id=doc_id,
        user_id="guest",
        created_at=datetime.now(timezone.utc)
    )
    db_with_document.add(bookmark)
    db_with_document.commit()

    response = client.get(f"/api/documents/{doc_id}/modal")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    # ブックマーク済み状態が反映されていることを確認
    # (HTMLにaria-pressed="true"が含まれているかチェック)
    assert 'aria-pressed="true"' in response.text or "bookmarked" in response.text.lower()

    # クリーンアップ
    db_with_document.query(Bookmark).filter(Bookmark.document_id == doc_id).delete()
    db_with_document.commit()


def test_document_card_has_modal_trigger(client: TestClient, db_with_document: Session):
    """記事カードの詳細ボタンがHTMXのモーダルトリガーを持つ"""
    # 記事一覧ページを取得
    response = client.get("/documents")

    assert response.status_code == 200
    html = response.text

    # 詳細を見るボタンがHTMX属性を持っていることを確認
    assert 'hx-get="/api/documents/' in html
    assert '/modal"' in html
    assert 'hx-target="#modal-container"' in html


def test_bookmark_api_returns_json_for_non_htmx_request(client: TestClient, db_with_document: Session):
    """非HTMXリクエストの場合、ブックマークAPIはJSONを返す"""
    doc_id = "test-doc-123"

    # HTMXヘッダーなしでブックマーク追加
    response = client.post("/api/bookmarks", json={"document_id": doc_id})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["bookmarked"] is True

    # クリーンアップ
    db_with_document.query(Bookmark).filter(Bookmark.document_id == doc_id).delete()
    db_with_document.commit()


def test_bookmark_api_returns_html_for_htmx_request(client: TestClient, db_with_document: Session):
    """HTMXリクエストの場合、ブックマークAPIはout-of-band swap用のHTMLを返す"""
    doc_id = "test-doc-123"

    # HTMXヘッダー付きでブックマーク追加
    response = client.post(
        "/api/bookmarks",
        json={"document_id": doc_id},
        headers={"HX-Request": "true"}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text

    # out-of-band swap用のHTML断片が含まれることを確認
    assert "hx-swap-oob" in html
    assert "modal-bookmark-btn" in html
    assert f"card-{doc_id}-bookmark" in html or "bookmark-btn" in html

    # クリーンアップ
    db_with_document.query(Bookmark).filter(Bookmark.document_id == doc_id).delete()
    db_with_document.commit()


def test_bookmark_delete_with_htmx(client: TestClient, db_with_document: Session):
    """HTMXリクエストでブックマーク削除し、out-of-band swap用のHTMLを返す"""
    doc_id = "test-doc-123"

    # ブックマークを追加
    bookmark = Bookmark(
        document_id=doc_id,
        user_id="guest",
        created_at=datetime.now(timezone.utc)
    )
    db_with_document.add(bookmark)
    db_with_document.commit()

    # HTMXヘッダー付きでブックマーク削除
    response = client.delete(
        f"/api/bookmarks?document_id={doc_id}",
        headers={"HX-Request": "true"}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text

    # out-of-band swap用のHTML断片が含まれることを確認
    assert "hx-swap-oob" in html
    assert 'aria-pressed="false"' in html or "bookmarked" not in html.lower()
