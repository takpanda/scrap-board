"""Test for 2-day filter on recommended articles."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import Document, create_tables
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


def test_personalized_sort_filters_to_recent_two_days(client: TestClient, db_session: Session):
    """パーソナライズドソートは直近2日間の記事のみを対象とすることを確認"""
    repo = PersonalizedScoreRepository(db_session)
    user_id = "guest"

    # 直近2日以内の記事を作成
    recent_doc_1 = _persist_document(
        db_session, 
        title="1日前の記事", 
        created_at=datetime.utcnow() - timedelta(days=1)
    )
    recent_doc_2 = _persist_document(
        db_session, 
        title="1.5日前の記事", 
        created_at=datetime.utcnow() - timedelta(days=1, hours=12)
    )
    
    # 2日より古い記事を作成
    old_doc_1 = _persist_document(
        db_session, 
        title="3日前の記事", 
        created_at=datetime.utcnow() - timedelta(days=3)
    )
    old_doc_2 = _persist_document(
        db_session, 
        title="5日前の記事", 
        created_at=datetime.utcnow() - timedelta(days=5)
    )

    # 全ての記事にPersonalizedScoreを設定（古い記事の方が高スコアに設定）
    scores = [
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=old_doc_1.id,
            score=0.95,  # 最も高いスコア
            rank=1,
            components=ExplanationBreakdown(similarity=0.9, category=0.8, domain=0.7, freshness=0.9),
            explanation="高スコアですが古いため除外される記事",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=old_doc_2.id,
            score=0.90,  # 2番目に高いスコア
            rank=2,
            components=ExplanationBreakdown(similarity=0.85, category=0.8, domain=0.7, freshness=0.85),
            explanation="高スコアですが古いため除外される記事",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=recent_doc_1.id,
            score=0.75,  # より低いスコア
            rank=3,
            components=ExplanationBreakdown(similarity=0.7, category=0.6, domain=0.5, freshness=0.8),
            explanation="最近の記事なので表示される",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=recent_doc_2.id,
            score=0.70,  # 最も低いスコア
            rank=4,
            components=ExplanationBreakdown(similarity=0.65, category=0.6, domain=0.5, freshness=0.75),
            explanation="最近の記事なので表示される",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
    ]
    repo.bulk_upsert(scores, profile_id=f"profile-{user_id}", user_id=user_id)

    # パーソナライズされたリストを取得
    response = client.get(
        "/api/documents",
        params={"sort": "personalized", "limit": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    docs = payload["documents"]
    
    # 結果に含まれるドキュメントのIDを取得
    doc_ids = [doc["id"] for doc in docs]
    
    # 2日より古い記事が結果に含まれていないことを確認
    assert old_doc_1.id not in doc_ids, "3日前の記事がおすすめリストに含まれています"
    assert old_doc_2.id not in doc_ids, "5日前の記事がおすすめリストに含まれています"
    
    # 直近2日以内の記事は含まれていることを確認
    assert recent_doc_1.id in doc_ids, "1日前の記事がおすすめリストに含まれていません"
    assert recent_doc_2.id in doc_ids, "1.5日前の記事がおすすめリストに含まれていません"
