"""Test for URL ingestion bug fix"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch

from app.core.database import Base, get_db

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

# Test DB setup
TEST_DB_PATH = "./test_url_ingestion_fix.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    """Test client with isolated database and dependency overrides applied."""
    Base.metadata.create_all(bind=engine)

    from app.main import app as _app

    _app.dependency_overrides[get_db] = override_get_db

    with TestClient(_app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)

def test_url_api_returns_json(client):
    """Test that the API endpoint returns JSON (current behavior)"""
    # Mock the content extractor
    mock_content_data = {
        "url": "https://example.com/test",
        "domain": "example.com", 
        "title": "Test Article",
        "content_md": "# Test\nTest content",
        "content_text": "Test content",
        "hash": "test123",
        "lang": "en"
    }
    
    with patch('app.services.extractor.content_extractor.extract_from_url', 
               new_callable=AsyncMock) as mock_extract:
        with patch('app.services.llm_client.llm_client.classify_content',
                   new_callable=AsyncMock) as mock_classify:
            with patch('app.services.llm_client.llm_client.create_embedding',
                       new_callable=AsyncMock) as mock_embed:
                
                mock_extract.return_value = mock_content_data
                mock_classify.return_value = {"primary_category": "テック", "tags": [], "confidence": 0.8}
                mock_embed.return_value = [0.1, 0.2, 0.3]
                
                # Submit URL via API
                response = client.post("/api/ingest/url", data={"url": "https://example.com/test"})
                
                # Should return JSON with success message
                assert response.status_code == 200
                assert response.headers.get("content-type") == "application/json"
                
                data = response.json()
                assert data["message"] == "Content ingested successfully"
                assert "document_id" in data
                assert data["title"] == "Test Article"

def test_home_page_has_ajax_form(client):
    """Test that the home page contains the AJAX URL form"""
    response = client.get("/")
    assert response.status_code == 200
    
    # Check that the form exists with the new AJAX structure
    content = response.text
    assert 'id="url-form"' in content
    assert 'name="url"' in content
    assert 'id="url-input"' in content
    assert 'type="submit"' in content
    
    # Should NOT have the old action attribute
    assert 'action="/api/ingest/url"' not in content
    
    # Should have the JavaScript handler
    assert 'getElementById(\'url-form\')' in content
    assert 'fetch(\'/api/ingest/url\'' in content

def test_api_error_handling(client):
    """Test that API errors are properly formatted for AJAX consumption"""
    # Test with no content extractor response (simulates network failure)
    with patch('app.services.extractor.content_extractor.extract_from_url', 
               new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = None  # Simulates extraction failure
        
        response = client.post("/api/ingest/url", data={"url": "https://invalid.example.com"})
        
        # Should return 400 with JSON error
        assert response.status_code == 400
        assert response.headers.get("content-type") == "application/json"
        
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Failed to extract content"

def test_javascript_includes_error_handling(client):
    """Test that the JavaScript includes proper error handling"""
    response = client.get("/")
    assert response.status_code == 200
    
    content = response.text
    
    # Check for error handling code (JS handler presence)
    assert 'catch (error)' in content
    assert 'text-red-600' in content

    # Check for success handling hints (status classes / redirect usage)
    assert 'text-green-600' in content or 'success' in content
    assert 'window.location.href' in content

    # Check for loading state by class (avoid relying on exact text)
    assert 'animate-pulse' in content or 'loading' in content
    assert 'submitBtn.disabled = true' in content

def test_form_submission_stays_on_page(client):
    """Test that form submission no longer redirects to JSON (this demonstrates the fix)"""
    # This test demonstrates the fix - previously the form would redirect to JSON
    # Now it uses AJAX so we stay on the same page
    
    response = client.get("/")
    assert response.status_code == 200
    
    # The page should contain the modal and AJAX submission code
    content = response.text
    assert 'fetch(\'/api/ingest/url\'' in content
    assert 'preventDefault()' in content
    
    # The old direct form submission should be gone
    assert 'method="post" action="/api/ingest/url"' not in content