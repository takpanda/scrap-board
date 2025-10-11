from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from dateutil.parser import isoparse
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from sqlalchemy.orm import Session

from app.core.database import Document, create_tables, Bookmark
from app.core import database as app_db
from app.services.personalization_models import ExplanationBreakdown, PersonalizedScoreDTO
from app.services.personalized_repository import PersonalizedScoreRepository


@pytest.fixture()
def client():
    """FastAPIクライアント。各テストで新しいDBスキーマを確保する。"""
    create_tables()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    create_tables()
    session = app_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _persist_document(session: Session, *, title: str, created_at: datetime | None = None) -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        url=f"https://example.com/{uuid.uuid4()}",
        domain="example.com",
        title=title,
        content_md="# heading\nbody",
        content_text="body",
        hash=str(uuid.uuid4()),
        created_at=created_at or datetime.utcnow(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def test_recent_sort_returns_jst_iso(client: TestClient, db_session: Session):
    db_session.query(Document).delete()
    db_session.commit()

    latest_created = datetime(2024, 1, 1, 0, 0)
    older_created = datetime(2023, 12, 31, 15, 0)

    latest_doc = _persist_document(db_session, title="最新記事", created_at=latest_created)
    older_doc = _persist_document(db_session, title="前日記事", created_at=older_created)

    response = client.get("/api/documents", params={"sort": "recent", "limit": 10})
    assert response.status_code == 200

    docs = response.json()["documents"]
    assert [doc["id"] for doc in docs[:2]] == [latest_doc.id, older_doc.id]

    first_created = docs[0]["created_at"]
    assert isinstance(first_created, str)
    assert first_created.endswith("+09:00")

    parsed_first = isoparse(first_created)
    assert parsed_first.tzinfo is not None
    expected_first = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc).astimezone(ZoneInfo("Asia/Tokyo"))
    assert parsed_first == expected_first

    parsed_second = isoparse(docs[1]["created_at"])
    expected_second = datetime(2023, 12, 31, 15, 0, tzinfo=timezone.utc).astimezone(ZoneInfo("Asia/Tokyo"))
    assert parsed_second == expected_second


def test_personalized_sort_returns_ranked_documents(client: TestClient, db_session: Session):
    repo = PersonalizedScoreRepository(db_session)

    # おすすめ記事は直近2日間の記事が対象なので、境界値を避けて1.5日前と0.5日前に設定
    # fallback_docは2日以内だがスコアを持たない記事
    first_doc = _persist_document(db_session, title="先頭に来る記事", created_at=datetime.utcnow() - timedelta(days=1, hours=12))
    second_doc = _persist_document(db_session, title="2番目の記事", created_at=datetime.utcnow() - timedelta(hours=12))
    fallback_doc = _persist_document(db_session, title="おすすめ外の記事", created_at=datetime.utcnow() - timedelta(hours=6))

    scores = [
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=first_doc.id,
            score=0.92,
            rank=1,
            components=ExplanationBreakdown(similarity=0.9, category=0.6, domain=0.3, freshness=0.8),
            explanation="最近の関心と強く一致しています。",
            computed_at=datetime.utcnow(),
            user_id="user-123",
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=second_doc.id,
            score=0.55,
            rank=2,
            components=ExplanationBreakdown(similarity=0.5, category=0.2, domain=0.1, freshness=0.6),
            explanation="関心にそこそこ一致しています。",
            computed_at=datetime.utcnow(),
            user_id="user-123",
            cold_start=False,
        ),
    ]
    repo.bulk_upsert(scores, profile_id="profile-user-123", user_id="user-123")

    response = client.get(
        "/api/documents",
        params={"sort": "personalized", "limit": 10},
        headers={"X-User-Id": "user-123"},
    )
    assert response.status_code == 200
    payload = response.json()

    docs = payload["documents"]
    assert [doc["id"] for doc in docs[:2]] == [first_doc.id, second_doc.id]

    assert docs[0]["personalized"]["rank"] == 1
    assert pytest.approx(docs[0]["personalized"]["score"], rel=1e-3) == 0.92
    assert "explanation" in docs[0]["personalized"]
    assert docs[0]["personalized"]["components"]["similarity"] == pytest.approx(0.9)

    assert "personalized" not in docs[-1]
    assert docs[-1]["id"] == fallback_doc.id


def test_personalized_sort_without_scores_returns_recent_order(client: TestClient, db_session: Session):
    # おすすめ記事は直近2日間の記事が対象なので、両方とも2日以内に設定
    first_doc = _persist_document(db_session, title="最新記事", created_at=datetime.utcnow())
    older_doc = _persist_document(db_session, title="古い記事", created_at=datetime.utcnow() - timedelta(days=1, hours=18))

    response = client.get(
        "/api/documents",
        params={"sort": "personalized", "limit": 10},
    )
    assert response.status_code == 200
    docs = response.json()["documents"]

    assert [doc["id"] for doc in docs] == [first_doc.id, older_doc.id]
    assert all("personalized" not in doc for doc in docs)


def test_personalized_sort_excludes_bookmarked_documents(client: TestClient, db_session: Session):
    """ブックマーク済みの記事はパーソナライズされたリストから除外されることを確認"""
    repo = PersonalizedScoreRepository(db_session)
    user_id = "user-123"

    # テスト用のドキュメントを作成
    bookmarked_doc = _persist_document(db_session, title="ブックマーク済み記事", created_at=datetime.utcnow() - timedelta(days=2))
    recommended_doc = _persist_document(db_session, title="おすすめ記事", created_at=datetime.utcnow() - timedelta(days=1))
    
    # 両方の記事にPersonalizedScoreを設定（ブックマーク済み記事の方が高スコア）
    scores = [
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=bookmarked_doc.id,
            score=0.95,  # より高いスコア
            rank=1,
            components=ExplanationBreakdown(similarity=0.9, category=0.8, domain=0.7, freshness=0.9),
            explanation="高スコアですがブックマーク済みのため除外される記事",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=recommended_doc.id,
            score=0.75,  # より低いスコア
            rank=2,
            components=ExplanationBreakdown(similarity=0.7, category=0.6, domain=0.5, freshness=0.8),
            explanation="ブックマークされていないおすすめ記事",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
    ]
    repo.bulk_upsert(scores, profile_id=f"profile-{user_id}", user_id=user_id)
    
    # bookmarked_docをブックマークに追加
    bookmark = Bookmark(
        user_id=user_id,
        document_id=bookmarked_doc.id,
        note="テスト用ブックマーク"
    )
    db_session.add(bookmark)
    db_session.commit()

    # パーソナライズされたリストを取得
    response = client.get(
        "/api/documents",
        params={"sort": "personalized", "limit": 10},
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 200
    payload = response.json()
    docs = payload["documents"]
    
    # ブックマーク済み記事が結果に含まれていないことを確認
    doc_ids = [doc["id"] for doc in docs]
    assert bookmarked_doc.id not in doc_ids, "ブックマーク済み記事がおすすめリストに含まれています"
    
    # ブックマークされていない記事は含まれていることを確認
    assert recommended_doc.id in doc_ids, "ブックマークされていない記事がおすすめリストに含まれていません"
    
    # ブックマークされていない記事がパーソナライズ情報を持っていることを確認
    recommended_doc_data = next((doc for doc in docs if doc["id"] == recommended_doc.id), None)
    assert recommended_doc_data is not None
    assert "personalized" in recommended_doc_data
    assert recommended_doc_data["personalized"]["score"] == pytest.approx(0.75, rel=1e-3)


def test_personalized_sort_uses_user_specific_scores_over_global(client: TestClient, db_session: Session):
    repo = PersonalizedScoreRepository(db_session)

    # おすすめ記事は直近2日間の記事が対象なので、2日以内に設定
    user_doc = _persist_document(db_session, title="ユーザー個別おすすめ", created_at=datetime.utcnow() - timedelta(days=1, hours=18))
    global_doc = _persist_document(db_session, title="グローバルおすすめ", created_at=datetime.utcnow() - timedelta(days=1, hours=12))
    fallback_doc = _persist_document(db_session, title="通常順序", created_at=datetime.utcnow())

    now = datetime.utcnow()

    repo.bulk_upsert(
        [
            PersonalizedScoreDTO(
                id=str(uuid.uuid4()),
                document_id=global_doc.id,
                score=0.9,
                rank=1,
                components=ExplanationBreakdown(similarity=0.8, category=0.5, domain=0.4, freshness=0.7),
                explanation="全体的に高評価です。",
                computed_at=now,
                user_id=None,
                cold_start=False,
            )
        ],
        profile_id="profile-global",
        user_id=None,
    )

    repo.bulk_upsert(
        [
            PersonalizedScoreDTO(
                id=str(uuid.uuid4()),
                document_id=user_doc.id,
                score=0.97,
                rank=1,
                components=ExplanationBreakdown(similarity=0.92, category=0.6, domain=0.3, freshness=0.8),
                explanation="あなたの嗜好に非常によく一致します。",
                computed_at=now,
                user_id="user-xyz",
                cold_start=True,
            )
        ],
        profile_id="profile-user-xyz",
        user_id="user-xyz",
    )

    response_user = client.get(
        "/api/documents",
        params={"sort": "personalized", "limit": 10},
        headers={"X-User-Id": "user-xyz"},
    )
    assert response_user.status_code == 200
    docs_user = response_user.json()["documents"]

    assert docs_user[0]["id"] == user_doc.id
    # コールドスタート記事は順序ランクを持たない（issue #18422667430 の修正に対応）
    assert docs_user[0]["personalized"]["rank"] is None
    assert docs_user[0]["personalized"]["cold_start"] is True
    assert docs_user[0]["personalized"]["components"]["similarity"] == pytest.approx(0.92)

    # 2番目はグローバルスコアを持つ記事（フォールバックとして使用される）
    assert docs_user[1]["id"] == global_doc.id
    assert "personalized" in docs_user[1]
    # グローバルスコアの記事は表示順で1番目のおすすめ記事なので rank=1
    assert docs_user[1]["personalized"]["rank"] == 1
    assert docs_user[1]["personalized"]["score"] == pytest.approx(0.9)
    
    # 3番目はスコアを持たない記事
    assert docs_user[2]["id"] == fallback_doc.id
    assert "personalized" not in docs_user[2]

    response_global = client.get(
        "/api/documents",
        params={"sort": "personalized", "limit": 10},
    )
    assert response_global.status_code == 200
    docs_global = response_global.json()["documents"]

    assert docs_global[0]["id"] == global_doc.id
    assert docs_global[0]["personalized"]["rank"] == 1
    assert docs_global[0]["personalized"]["cold_start"] is False
    fallback_ids = {doc["id"] for doc in docs_global[1:]}
    assert fallback_ids == {fallback_doc.id, user_doc.id}
    for doc in docs_global[1:]:
        assert "personalized" not in doc