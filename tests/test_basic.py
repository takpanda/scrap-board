import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

# テスト用インメモリデータベース
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    # テスト用データベースの作成
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    # テスト後にクリーンアップ
    Base.metadata.drop_all(bind=engine)

def test_health_endpoint(client):
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"

def test_home_page(client):
    """ホームページのテスト"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Scrap-Board" in response.text

def test_documents_page(client):
    """ドキュメントページのテスト"""
    response = client.get("/documents")
    assert response.status_code == 200
    assert "ドキュメント一覧" in response.text

def test_empty_documents_list(client):
    """空のドキュメントリストAPIのテスト"""
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["documents"] == []
    assert data["total"] == 0

def test_stats_endpoint(client):
    """統計エンドポイントのテスト"""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "today_documents" in data
    assert "total_categories" in data
    assert "total_collections" in data
    assert data["total_documents"] == 0  # 初期状態

def test_search_endpoint(client):
    """検索エンドポイントのテスト"""
    response = client.get("/api/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert data["results"] == []  # 初期状態では何も見つからない

def test_search_short_query(client):
    """短すぎる検索クエリのテスト"""
    response = client.get("/api/search?q=a")
    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []
    assert data["total"] == 0

# 実際のURL取り込みテストは外部依存があるため、モックまたはローカルファイルでテスト
@pytest.mark.skip(reason="Requires external dependencies and LLM service")
def test_url_ingestion(client):
    """URL取り込みのテスト（スキップ）"""
    response = client.post("/api/ingest/url", data={"url": "https://example.com"})
    # 実際のテストでは適切なモックが必要
    pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])