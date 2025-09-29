import json
import uuid
from datetime import datetime, timedelta

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, Document, PersonalizedScore, get_db

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

# Test DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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
    # テスト用データベースの作成
    Base.metadata.create_all(bind=engine)

    # Import app lazily so dependency overrides apply
    from app.main import app as _app

    _app.dependency_overrides[get_db] = override_get_db

    with TestClient(_app) as test_client:
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
    # ヘッダーのテキストはSVGロゴに置き換えられたので、imgタグとlogo.svg参照を検査する
    assert "<img" in response.text
    assert "/static/images/logo.svg" in response.text

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


def _create_document(session, *, doc_id: str, title: str, created_at: datetime) -> None:
    session.add(
        Document(
            id=doc_id,
            url=f"https://example.com/{doc_id}",
            domain="example.com",
            title=title,
            author="テスト",
            published_at=None,
            fetched_at=None,
            lang="ja",
            content_md=f"# {title}\n本文",
            content_text=f"{title} の本文",
            hash=f"hash-{doc_id}",
            created_at=created_at,
            updated_at=created_at,
        )
    )


def _add_personalized_score(
    session,
    *,
    document_id: str,
    rank: int,
    score: float,
    explanation: str,
    computed_at: datetime,
    user_id: str | None = None,
) -> None:
    payload = json.dumps(
        {
            "similarity": 0.4,
            "category": 0.3,
            "domain": 0.2,
            "freshness": 0.1,
            "__cold_start": False,
        },
        ensure_ascii=False,
    )

    session.add(
        PersonalizedScore(
            id=str(uuid.uuid4()),
            profile_id=None,
            user_id=user_id,
            document_id=document_id,
            score=score,
            rank=rank,
            components=payload,
            explanation=explanation,
            computed_at=computed_at,
        )
    )


def test_documents_personalized_sort_with_scores(client):
    session = TestingSessionLocal()
    try:
        now = datetime.utcnow()
        doc_recent_id = "doc-recent"
        doc_rank1_id = "doc-rank1"
        doc_rank2_id = "doc-rank2"

        _create_document(session, doc_id=doc_recent_id, title="最新ドキュメント", created_at=now)
        _create_document(session, doc_id=doc_rank1_id, title="おすすめ1", created_at=now - timedelta(hours=1))
        _create_document(session, doc_id=doc_rank2_id, title="おすすめ2", created_at=now - timedelta(days=1))
        session.commit()

        _add_personalized_score(
            session,
            document_id=doc_rank1_id,
            rank=1,
            score=0.92,
            explanation="推薦理由1",
            computed_at=now,
            user_id=None,
        )
        _add_personalized_score(
            session,
            document_id=doc_rank2_id,
            rank=2,
            score=0.81,
            explanation="推薦理由2",
            computed_at=now - timedelta(minutes=5),
            user_id=None,
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/api/documents", params={"sort": "personalized", "limit": 5})
    assert response.status_code == 200
    data = response.json()

    ids = [doc["id"] for doc in data["documents"]]
    assert ids[:3] == [doc_rank1_id, doc_rank2_id, doc_recent_id]

    top_entry = data["documents"][0]
    assert top_entry["personalized"]["rank"] == 1
    assert top_entry["personalized"]["score"] == pytest.approx(0.92, rel=1e-6)
    assert "components" in top_entry["personalized"]

    fallback_entry = data["documents"][2]
    assert "personalized" not in fallback_entry


def test_documents_personalized_sort_respects_user_header(client):
    session = TestingSessionLocal()
    try:
        now = datetime.utcnow()
        doc_default_id = "doc-default"
        doc_user_id = "doc-user"

        _create_document(session, doc_id=doc_default_id, title="通常ソート", created_at=now)
        _create_document(session, doc_id=doc_user_id, title="ユーザー向け", created_at=now - timedelta(hours=2))
        session.commit()

        _add_personalized_score(
            session,
            document_id=doc_user_id,
            rank=1,
            score=0.97,
            explanation="ユーザー向け推薦",
            computed_at=now,
            user_id="user-123",
        )
        session.commit()
    finally:
        session.close()

    default_response = client.get("/api/documents", params={"sort": "personalized"})
    assert default_response.status_code == 200
    default_ids = [doc["id"] for doc in default_response.json()["documents"]]
    assert default_ids[0] == doc_default_id
    assert "personalized" not in default_response.json()["documents"][0]

    header_response = client.get(
        "/api/documents",
        params={"sort": "personalized"},
        headers={"X-User-Id": "user-123"},
    )
    assert header_response.status_code == 200
    header_data = header_response.json()["documents"]
    assert header_data[0]["id"] == doc_user_id
    assert header_data[0]["personalized"]["rank"] == 1
    assert header_data[1]["id"] == doc_default_id
    assert "personalized" not in header_data[1]

def test_environment_configuration():
    """環境変数設定のテスト"""
    from app.core.config import settings
    
    # 設定が正しく読み込まれることを確認
    assert settings.db_url is not None
    assert settings.chat_api_base is not None
    assert settings.chat_model is not None
    assert settings.embed_api_base is not None
    assert settings.embed_model is not None
    assert settings.timeout_sec > 0
    
    # デフォルト値の確認
    assert "sqlite:///" in settings.db_url
    assert "v1" in settings.chat_api_base
    assert "v1" in settings.embed_api_base

# 実際のURL取り込みテストは外部依存があるため、モックまたはローカルファイルでテスト
@pytest.mark.skip(reason="Requires external dependencies and LLM service")
def test_url_ingestion(client):
    """URL取り込みのテスト（スキップ）"""
    response = client.post("/api/ingest/url", data={"url": "https://example.com"})
    # 実際のテストでは適切なモックが必要
    pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])