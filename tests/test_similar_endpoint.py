"""
Test for the similar documents endpoint functionality
"""
import pytest
import uuid
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db, Document, Classification

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

# Test DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_similar.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    # テスト用データベースの作成
    Base.metadata.create_all(bind=engine)

    # Import app lazily so dependency overrides can be applied
    from app.main import app as _app

    _app.dependency_overrides[get_db] = override_get_db

    with TestClient(_app) as test_client:
        yield test_client

    # テスト後にクリーンアップ
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_documents():
    """Create test documents for similar document testing"""
    db = TestingSessionLocal()
    
    # Use unique identifiers for URLs to avoid conflicts
    test_id = str(uuid.uuid4())[:8]
    
    try:
        # Create first document
        doc1_content = "This is a test article about artificial intelligence and machine learning."
        doc1 = Document(
            id=str(uuid.uuid4()),
            title="AI and ML Article",
            content_md=doc1_content,
            content_text=doc1_content,
            hash=hashlib.md5(doc1_content.encode()).hexdigest(),
            url=f"https://test.example.com/ai-article-{test_id}",
            domain="test.example.com",
            lang="en"
        )
        db.add(doc1)
        db.flush()  # Flush to get the ID
        
        # Add classification for doc1
        classification1 = Classification(
            document_id=doc1.id,
            primary_category="テック/AI",
            topics=["人工知能", "機械学習"],
            tags=["AI", "ML", "テクノロジー"],
            confidence=0.9,
            method="rules"
        )
        db.add(classification1)
        
        # Create second document in same category
        doc2_content = "Deep learning is a subset of machine learning that uses neural networks."
        doc2 = Document(
            id=str(uuid.uuid4()),
            title="Deep Learning Basics",
            content_md=doc2_content,
            content_text=doc2_content,
            hash=hashlib.md5(doc2_content.encode()).hexdigest(),
            url=f"https://test.example.com/deep-learning-{test_id}",
            domain="test.example.com",
            lang="en"
        )
        db.add(doc2)
        db.flush()  # Flush to get the ID
        
        # Add classification for doc2
        classification2 = Classification(
            document_id=doc2.id,
            primary_category="テック/AI",
            topics=["深層学習", "ニューラルネットワーク"],
            tags=["ディープラーニング", "AI", "テクノロジー"],
            confidence=0.95,
            method="rules"
        )
        db.add(classification2)
        
        # Create third document in different category
        doc3_content = "Cooking pasta requires boiling water and adding salt."
        doc3 = Document(
            id=str(uuid.uuid4()),
            title="Pasta Cooking Guide",
            content_md=doc3_content,
            content_text=doc3_content,
            hash=hashlib.md5(doc3_content.encode()).hexdigest(),
            url=f"https://test.example.com/pasta-cooking-{test_id}",
            domain="test.example.com", 
            lang="en"
        )
        db.add(doc3)
        db.flush()  # Flush to get the ID
        
        # Add classification for doc3
        classification3 = Classification(
            document_id=doc3.id,
            primary_category="生活/料理",
            topics=["料理", "パスタ"],
            tags=["料理", "食べ物"],
            confidence=0.85,
            method="rules"
        )
        db.add(classification3)
        
        db.commit()
        
        yield doc1.id, doc2.id, doc3.id
        
    finally:
        # Cleanup - need to refresh objects and delete in correct order
        try:
            db.rollback()
            # Delete by ID to avoid object state issues
            db.query(Classification).filter(Classification.document_id.in_([doc1.id, doc2.id, doc3.id])).delete()
            db.query(Document).filter(Document.id.in_([doc1.id, doc2.id, doc3.id])).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_similar_documents_json_endpoint(client, test_documents):
    """Test similar documents endpoint returns JSON by default"""
    doc1_id, doc2_id, doc3_id = test_documents
    
    response = client.get(f"/api/documents/{doc1_id}/similar")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "similar_documents" in data
    similar_docs = data["similar_documents"]
    assert len(similar_docs) == 1  # Only doc2 should be similar (same category)
    assert similar_docs[0]["id"] == doc2_id
    assert similar_docs[0]["title"] == "Deep Learning Basics"
    assert "similarity_score" in similar_docs[0]


def test_similar_documents_htmx_endpoint(client, test_documents):
    """Test similar documents endpoint returns HTML when called with HX-Request header"""
    doc1_id, doc2_id, doc3_id = test_documents
    
    response = client.get(
        f"/api/documents/{doc1_id}/similar",
        headers={"HX-Request": "true"}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    
    # Check that HTML contains expected elements
    html_content = response.text
    assert "Deep Learning Basics" in html_content
    # Ensure the document link and domain appear
    assert f"/documents/{doc2_id}" in html_content
    assert "test.example.com" in html_content
    # If a numeric similarity percentage is present, ensure it's a valid number
    import re
    similarity_match = re.search(r'類似度:\s*(\d+(?:\.\d+)?)%', html_content)
    if similarity_match:
        similarity_score = float(similarity_match.group(1))
        assert 0.0 <= similarity_score <= 100.0


def test_similar_documents_not_found(client):
    """Test similar documents endpoint with non-existent document"""
    non_existent_id = str(uuid.uuid4())
    
    response = client.get(f"/api/documents/{non_existent_id}/similar")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_similar_documents_no_classification(client):
    """Test similar documents endpoint for document without classification"""
    db = TestingSessionLocal()
    doc = None
    
    try:
        # Create document without classification
        doc_content = "Document without classification"
        doc = Document(
            id=str(uuid.uuid4()),
            title="Unclassified Document",
            content_md=doc_content,
            content_text=doc_content,
            hash=hashlib.md5(doc_content.encode()).hexdigest(),
            url=f"https://test.example.com/unclassified-{uuid.uuid4()}",
            domain="test.example.com",
            lang="en"
        )
        db.add(doc)
        db.commit()
        
        response = client.get(f"/api/documents/{doc.id}/similar")
        
        assert response.status_code == 200
        data = response.json()
        assert data["similar_documents"] == []  # No similar docs without classification
        
    finally:
        if doc:
            try:
                db.delete(doc)
                db.commit()
            except Exception:
                db.rollback()
        db.close()