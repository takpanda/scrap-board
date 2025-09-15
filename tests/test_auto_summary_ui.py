"""
Test for auto-summary UI functionality in document detail page
"""
import pytest
import os
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, Document, get_db

# Test database path
TEST_DB_PATH = "test_auto_summary.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{TEST_DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


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



@pytest.fixture(scope="function")
def client():
    """Create a TestClient after DB setup to ensure tables exist and override dependencies."""
    # Import app lazily so dependency overrides are applied
    from app.main import app as _app

    _app.dependency_overrides[get_db] = override_get_db

    with TestClient(_app) as test_client:
        yield test_client


@pytest.fixture
def test_document():
    """テスト用ドキュメントの作成（各テストで一意のURL）"""
    db = TestingSessionLocal()
    try:
        document_id = str(uuid.uuid4())
        unique_url = f"https://example.com/test-auto-summary-{document_id[:8]}"
        
        document = Document(
            id=document_id,
            url=unique_url,
            domain="example.com",
            title="Test Auto Summary Article",
            author="Test Author",
            content_md="# Test Article\n\nThis is a test article for auto-summary functionality.",
            content_text="Test Article\n\nThis is a test article for auto-summary functionality.",
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
def test_document_detail_page_renders_with_auto_summary_section(mock_summarize, test_document, client):
    """ドキュメント詳細ページが要約セクションを表示状態でレンダリングされることを確認"""
    # Test document detail page
    response = client.get(f"/documents/{test_document.id}")
    
    assert response.status_code == 200
    html_content = response.text
    
    # Verify summary section is visible (not hidden)
    assert 'id="summary-section"' in html_content
    # Template uses dify classes; check for summary container instead of old class names
    assert 'dify-content-card' in html_content
    assert 'dify-summary-content' in html_content
    
    # Verify toggle button exists and has correct initial text
    assert 'id="content-view-toggle"' in html_content
    assert '全文を表示' in html_content
    
    # Verify auto-loading script is present
    assert 'autoLoadSummary()' in html_content
    assert 'document.addEventListener(\'DOMContentLoaded\'' in html_content
    
    # Verify content section is hidden by default
    assert 'id="content-section"' in html_content
    assert 'class="hidden dify-content-card' in html_content or 'class="hidden content-section' in html_content


def test_summary_section_structure_in_html(test_document, client):
    """要約セクションが正しい構造でHTMLに含まれることを確認"""
    # Get page HTML
    response = client.get(f"/documents/{test_document.id}")
    html_content = response.text
    
    # Verify summary section has correct elements
    assert 'AI要約' in html_content
    assert 'id="summary-content"' in html_content
    assert 'animate-pulse' in html_content  # Loading animation
    
    # Verify toggle functionality elements
    assert 'toggleContentView()' in html_content
    assert 'showingSummary = true' in html_content  # Initial state