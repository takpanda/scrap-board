"""テスト: 要約エンドポイント"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db, Document
import uuid
import os


# テスト用データベース
TEST_DB_PATH = "./test_summarize.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """テスト用データベースセッション"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()



app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create a TestClient for each test after DB setup."""
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """テストセッション全体でのデータベースセットアップ"""
    # テストデータベースを削除（存在する場合）
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # テストデータベースのセットアップ
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # クリーンアップ
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
def sample_document():
    """テスト用ドキュメントの作成（各テストで一意のURL）"""
    db = TestingSessionLocal()
    try:
        document_id = str(uuid.uuid4())
        unique_url = f"https://example.com/test-article-{document_id[:8]}"
        
        document = Document(
            id=document_id,
            url=unique_url,
            domain="example.com",
            title="Test Article",
            author="Test Author",
            content_md="# Test Article\n\nThis is a test article content.",
            content_text="Test Article\n\nThis is a test article content.",
            hash=f"test-hash-{document_id[:8]}",
            lang="ja"
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    finally:
        db.close()


def test_summarize_endpoint_not_found(client):
    """存在しないドキュメントの要約リクエスト"""
    non_existent_id = str(uuid.uuid4())
    response = client.post(f"/api/documents/{non_existent_id}/summarize")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@patch('app.api.routes.documents.llm_client.summarize_text')
def test_summarize_endpoint_success(mock_summarize, sample_document, client):
    """正常な要約生成"""
    # LLMクライアントのモック設定 - AsyncMockを使わずに直接戻り値を設定
    mock_summarize.return_value = "これはテスト記事の要約です。"
    
    response = client.post(f"/api/documents/{sample_document.id}/summarize")
    
    assert response.status_code == 200
    data = response.json()
    assert "short_summary" in data
    assert isinstance(data["short_summary"], str)
    # モックが呼ばれたことを確認
    mock_summarize.assert_called_once()


@patch('app.api.routes.documents.llm_client.summarize_text')
def test_summarize_endpoint_llm_failure(mock_summarize, sample_document, client):
    """LLM要約生成失敗時の処理"""
    # LLMクライアントが None を返すケース
    mock_summarize.return_value = None
    
    response = client.post(f"/api/documents/{sample_document.id}/summarize")
    
    assert response.status_code == 200
    data = response.json()
    assert "short_summary" in data
    assert "LLMサービスに接続できませんでした" in data["short_summary"]


@patch('app.api.routes.documents.llm_client.summarize_text')
def test_summarize_endpoint_exception(mock_summarize, sample_document, client):
    """LLM要約生成で例外が発生した場合の処理"""
    # LLMクライアントが例外を投げるケース
    mock_summarize.side_effect = Exception("LLM service error")
    
    response = client.post(f"/api/documents/{sample_document.id}/summarize")
    
    assert response.status_code == 200
    data = response.json()
    assert "short_summary" in data
    assert "エラーが発生しました" in data["short_summary"]


def test_summarize_endpoint_response_format(sample_document, client):
    """レスポンス形式の確認（LLMサービスなしでも基本的なレスポンス形式をチェック）"""
    response = client.post(f"/api/documents/{sample_document.id}/summarize")
    
    assert response.status_code == 200
    data = response.json()
    
    # 期待されるフィールドが存在することを確認
    assert "short_summary" in data
    assert isinstance(data["short_summary"], str)
    assert len(data["short_summary"]) > 0