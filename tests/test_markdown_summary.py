"""テスト: Markdown要約表示機能"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db, Document
import uuid
import os


# テスト用データベース
TEST_DB_PATH = "./test_markdown_summary.db"
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

client = TestClient(app)


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
    """テスト用ドキュメントの作成"""
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


@patch('app.api.routes.documents.llm_client.summarize_text')
def test_summarize_endpoint_returns_markdown(mock_summarize, sample_document):
    """要約エンドポイントがMarkdown形式のコンテンツを返すことのテスト"""
    # LLMクライアントがMarkdown形式の要約を返すように設定
    markdown_summary = "## 要約\n\nこれは**重要な**記事です。\n\n- ポイント1\n- ポイント2\n\n`コード例`もあります。"
    mock_summarize.return_value = markdown_summary
    
    response = client.post(f"/api/documents/{sample_document.id}/summarize")
    
    assert response.status_code == 200
    data = response.json()
    assert "short_summary" in data
    assert isinstance(data["short_summary"], str)
    assert "**重要な**" in data["short_summary"]  # Markdownフォーマットが保持されていることを確認
    assert "- ポイント1" in data["short_summary"]  # リストフォーマットが保持されていることを確認


def test_document_detail_page_includes_markdown_function(sample_document):
    """ドキュメント詳細ページにMarkdown変換関数が含まれていることのテスト"""
    response = client.get(f"/documents/{sample_document.id}")
    
    assert response.status_code == 200
    html_content = response.text
    
    # JavaScript内にmarkdownToHtml関数が存在することを確認
    assert "function markdownToHtml(" in html_content
    assert "markdownToHtml(data.short_summary" in html_content
    
    # proseクラスが要約セクションに適用されていることを確認
    assert 'prose prose-sm max-w-none' in html_content


@patch('app.api.routes.documents.llm_client.summarize_text')
def test_summarize_with_various_markdown_formats(mock_summarize, sample_document):
    """様々なMarkdown形式での要約のテスト"""
    test_cases = [
        {
            "input": "# 見出し1\n## 見出し2\n### 見出し3",
            "name": "headers"
        },
        {
            "input": "**太字** と *斜体* のテスト",
            "name": "emphasis"
        },
        {
            "input": "- 項目1\n- 項目2\n- 項目3",
            "name": "lists"
        },
        {
            "input": "`inline code` と ```\ncode block\n```",
            "name": "code"
        }
    ]
    
    for test_case in test_cases:
        mock_summarize.return_value = test_case["input"]
        
        response = client.post(f"/api/documents/{sample_document.id}/summarize")
        
        assert response.status_code == 200
        data = response.json()
        assert data["short_summary"] == test_case["input"]