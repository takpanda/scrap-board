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


def test_personalized_sort_returns_ranked_documents(client: TestClient, db_session: Session):
    repo = PersonalizedScoreRepository(db_session)

    first_doc = _persist_document(db_session, title="先頭に来る記事", created_at=datetime.utcnow() - timedelta(days=2))
    second_doc = _persist_document(db_session, title="2番目の記事", created_at=datetime.utcnow() - timedelta(days=1))
    fallback_doc = _persist_document(db_session, title="おすすめ外の記事", created_at=datetime.utcnow())

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
    first_doc = _persist_document(db_session, title="最新記事", created_at=datetime.utcnow())
    older_doc = _persist_document(db_session, title="古い記事", created_at=datetime.utcnow() - timedelta(days=3))

    response = client.get(
        "/api/documents",
        params={"sort": "personalized", "limit": 10},
    )
    assert response.status_code == 200
    docs = response.json()["documents"]

    assert [doc["id"] for doc in docs] == [first_doc.id, older_doc.id]
    assert all("personalized" not in doc for doc in docs)
    assert all("personalized" not in doc for doc in docs)


def test_personalized_sort_uses_user_specific_scores_over_global(client: TestClient, db_session: Session):
    repo = PersonalizedScoreRepository(db_session)

    user_doc = _persist_document(db_session, title="ユーザー個別おすすめ", created_at=datetime.utcnow() - timedelta(days=5))
    global_doc = _persist_document(db_session, title="グローバルおすすめ", created_at=datetime.utcnow() - timedelta(days=4))
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
    assert docs_user[0]["personalized"]["rank"] == 1
    assert docs_user[0]["personalized"]["cold_start"] is True
    assert docs_user[0]["personalized"]["components"]["similarity"] == pytest.approx(0.92)

    remaining_user_ids = {doc["id"] for doc in docs_user[1:]}
    assert remaining_user_ids == {fallback_doc.id, global_doc.id}
    for doc in docs_user[1:]:
        assert "personalized" not in doc

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