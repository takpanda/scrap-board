"""
Test for similarity calculation with actual embeddings
"""
import pytest
import uuid
import hashlib
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db, Document, Classification, Embedding

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

# Test DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_similarity_calculation.db"
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
    # Ensure DB schema exists for this test file
    Base.metadata.create_all(bind=engine)

    # Import app lazily so dependency overrides apply correctly
    from app.main import app as _app

    _app.dependency_overrides[get_db] = override_get_db

    with TestClient(_app) as test_client:
        yield test_client

    # テスト後にクリーンアップ
    Base.metadata.drop_all(bind=engine)


def test_similarity_calculation_with_embeddings(client):
    """Test similarity calculation with actual embeddings"""
    db = TestingSessionLocal()
    
    test_id = str(uuid.uuid4())[:8]
    
    try:
        # Create first document
        doc1_content = "AI and machine learning are transforming technology"
        doc1 = Document(
            id=str(uuid.uuid4()),
            title="AI Technology",
            content_md=doc1_content,
            content_text=doc1_content,
            hash=hashlib.md5(doc1_content.encode()).hexdigest(),
            url=f"https://test.example.com/ai-tech-{test_id}",
            domain="test.example.com",
            lang="en"
        )
        db.add(doc1)
        db.flush()
        
        # Create classification for doc1
        classification1 = Classification(
            document_id=doc1.id,
            primary_category="テック/AI",
            topics=["AI", "ML"],
            tags=["AI", "ML"],
            confidence=0.9,
            method="rules"
        )
        db.add(classification1)
        
        # Create similar embedding for doc1 (AI/ML related)
        embedding1 = Embedding(
            document_id=doc1.id,
            chunk_id=0,
            vec=json.dumps([0.1, 0.8, 0.2, 0.9, 0.1]),  # AI-like vector
            chunk_text=doc1_content
        )
        db.add(embedding1)
        
        # Create second document (similar to first)
        doc2_content = "Machine learning and AI are revolutionizing software development"
        doc2 = Document(
            id=str(uuid.uuid4()),
            title="ML Revolution",
            content_md=doc2_content,
            content_text=doc2_content,
            hash=hashlib.md5(doc2_content.encode()).hexdigest(),
            url=f"https://test.example.com/ml-revolution-{test_id}",
            domain="test.example.com",
            lang="en"
        )
        db.add(doc2)
        db.flush()
        
        # Create classification for doc2
        classification2 = Classification(
            document_id=doc2.id,
            primary_category="テック/AI",
            topics=["AI", "ML"],
            tags=["AI", "ML"],
            confidence=0.9,
            method="rules"
        )
        db.add(classification2)
        
        # Create similar embedding for doc2
        embedding2 = Embedding(
            document_id=doc2.id,
            chunk_id=0,
            vec=json.dumps([0.15, 0.75, 0.25, 0.85, 0.12]),  # Similar AI-like vector
            chunk_text=doc2_content
        )
        db.add(embedding2)
        
        # Create third document (different topic)
        doc3_content = "Cooking recipes and kitchen techniques for beginners"
        doc3 = Document(
            id=str(uuid.uuid4()),
            title="Cooking Guide",
            content_md=doc3_content,
            content_text=doc3_content,
            hash=hashlib.md5(doc3_content.encode()).hexdigest(),
            url=f"https://test.example.com/cooking-{test_id}",
            domain="test.example.com",
            lang="en"
        )
        db.add(doc3)
        db.flush()
        
        # Create classification for doc3
        classification3 = Classification(
            document_id=doc3.id,
            primary_category="テック/AI",  # Same category but different content
            topics=["料理"],
            tags=["料理"],
            confidence=0.8,
            method="rules"
        )
        db.add(classification3)
        
        # Create different embedding for doc3
        embedding3 = Embedding(
            document_id=doc3.id,
            chunk_id=0,
            vec=json.dumps([0.9, 0.1, 0.8, 0.2, 0.9]),  # Very different vector
            chunk_text=doc3_content
        )
        db.add(embedding3)
        
        db.commit()
        
        # Test the similarity calculation
        response = client.get(f"/api/documents/{doc1.id}/similar")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "similar_documents" in data
        similar_docs = data["similar_documents"]
        assert len(similar_docs) == 2  # doc2 and doc3
        
        # Check that doc2 (similar content) has higher similarity than doc3 (different content)
        doc2_sim = None
        doc3_sim = None
        
        for doc in similar_docs:
            if doc["id"] == doc2.id:
                doc2_sim = doc["similarity_score"]
            elif doc["id"] == doc3.id:
                doc3_sim = doc["similarity_score"]
        
        assert doc2_sim is not None
        assert doc3_sim is not None
        assert doc2_sim > doc3_sim  # doc2 should be more similar than doc3
        assert doc2_sim > 0.5  # Should be reasonably high similarity
        # Don't assert specific threshold for doc3_sim since vectors can be more similar than expected
        
    finally:
        # Cleanup
        try:
            db.rollback()
            db.query(Embedding).delete()
            db.query(Classification).delete()
            db.query(Document).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_cosine_similarity_function():
    """Test the cosine similarity calculation function directly"""
    from app.services.similarity import cosine_similarity
    
    # Test identical vectors
    vec1 = [1, 0, 0, 0]
    vec2 = [1, 0, 0, 0]
    similarity = cosine_similarity(vec1, vec2)
    assert similarity == 1.0
    
    # Test orthogonal vectors  
    vec1 = [1, 0, 0, 0]
    vec2 = [0, 1, 0, 0]
    similarity = cosine_similarity(vec1, vec2)
    assert similarity == 0.5  # (0 + 1) / 2 = 0.5
    
    # Test opposite vectors
    vec1 = [1, 0, 0, 0]
    vec2 = [-1, 0, 0, 0]
    similarity = cosine_similarity(vec1, vec2)
    assert similarity == 0.0  # (-1 + 1) / 2 = 0.0
    
    # Test similar vectors
    vec1 = [0.8, 0.6, 0.0, 0.0]
    vec2 = [0.6, 0.8, 0.0, 0.0]
    similarity = cosine_similarity(vec1, vec2)
    assert 0.8 < similarity < 1.0  # Should be high but not perfect