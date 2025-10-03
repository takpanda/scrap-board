"""
Test for rank reassignment when documents are filtered out.

This test verifies that ranks are consecutive (1, 2, 3...) in the API response,
even when some documents are filtered out (e.g., bookmarked documents).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

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


def test_rank_reassignment_when_documents_filtered_out(client: TestClient, db_session: Session):
    """
    ブックマーク済みなどで一部のドキュメントが除外された場合に、
    表示される記事のrankが連続していることを確認する。
    
    例: rank 1, 2, 3, 4, 5 のうち、2と4がフィルタされた場合、
    表示される記事のrankは 1, 2, 3 と連番で再割当てされる。
    """
    repo = PersonalizedScoreRepository(db_session)
    user_id = "user-test-rank"

    # 5つの記事を作成
    doc1 = _persist_document(db_session, title="記事1", created_at=datetime.utcnow() - timedelta(days=5))
    doc2 = _persist_document(db_session, title="記事2 (ブックマーク済み)", created_at=datetime.utcnow() - timedelta(days=4))
    doc3 = _persist_document(db_session, title="記事3", created_at=datetime.utcnow() - timedelta(days=3))
    doc4 = _persist_document(db_session, title="記事4 (ブックマーク済み)", created_at=datetime.utcnow() - timedelta(days=2))
    doc5 = _persist_document(db_session, title="記事5", created_at=datetime.utcnow() - timedelta(days=1))

    # 全ての記事にPersonalizedScoreを設定 (rank 1-5)
    scores = [
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=doc1.id,
            score=0.95,
            rank=1,  # DB rank = 1
            components=ExplanationBreakdown(similarity=0.9, category=0.8, domain=0.7, freshness=0.9),
            explanation="第1位の記事",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=doc2.id,
            score=0.85,
            rank=2,  # DB rank = 2 (will be filtered out)
            components=ExplanationBreakdown(similarity=0.8, category=0.7, domain=0.6, freshness=0.8),
            explanation="第2位の記事（ブックマーク済みなので除外される）",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=doc3.id,
            score=0.75,
            rank=3,  # DB rank = 3
            components=ExplanationBreakdown(similarity=0.7, category=0.6, domain=0.5, freshness=0.7),
            explanation="第3位の記事",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=doc4.id,
            score=0.65,
            rank=4,  # DB rank = 4 (will be filtered out)
            components=ExplanationBreakdown(similarity=0.6, category=0.5, domain=0.4, freshness=0.6),
            explanation="第4位の記事（ブックマーク済みなので除外される）",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
        PersonalizedScoreDTO(
            id=str(uuid.uuid4()),
            document_id=doc5.id,
            score=0.55,
            rank=5,  # DB rank = 5
            components=ExplanationBreakdown(similarity=0.5, category=0.4, domain=0.3, freshness=0.5),
            explanation="第5位の記事",
            computed_at=datetime.utcnow(),
            user_id=user_id,
            cold_start=False,
        ),
    ]
    repo.bulk_upsert(scores, profile_id=f"profile-{user_id}", user_id=user_id)

    # doc2とdoc4をブックマークに追加（これらが除外される）
    for doc_id in [doc2.id, doc4.id]:
        bookmark = Bookmark(
            user_id=user_id,
            document_id=doc_id,
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

    # ブックマーク済み記事が除外されていることを確認
    doc_ids = [doc["id"] for doc in docs]
    assert doc2.id not in doc_ids, "ブックマーク済みdoc2が除外されていません"
    assert doc4.id not in doc_ids, "ブックマーク済みdoc4が除外されていません"

    # 残った記事を取得
    remaining_docs = [doc for doc in docs if "personalized" in doc]
    assert len(remaining_docs) == 3, f"おすすめ記事が3件あるべきですが{len(remaining_docs)}件です"

    # 期待される順序: doc1 (DB rank 1), doc3 (DB rank 3), doc5 (DB rank 5)
    expected_ids = [doc1.id, doc3.id, doc5.id]
    actual_ids = [doc["id"] for doc in remaining_docs]
    assert actual_ids == expected_ids, f"記事の順序が期待と異なります: {actual_ids} != {expected_ids}"

    # ここが重要: 表示されるrankは連続しているべき (1, 2, 3)
    display_ranks = [doc["personalized"]["rank"] for doc in remaining_docs]
    expected_ranks = [1, 2, 3]  # 連続した番号
    assert display_ranks == expected_ranks, (
        f"Rankが連続していません: {display_ranks} != {expected_ranks}. "
        f"期待される動作: DBのrank値に関係なく、表示される記事には1から連番でrankが割り当てられるべき。"
    )

    # 各記事の詳細を確認
    assert remaining_docs[0]["title"] == "記事1"
    assert remaining_docs[0]["personalized"]["rank"] == 1, "doc1のrankは1であるべき"
    assert pytest.approx(remaining_docs[0]["personalized"]["score"], rel=1e-3) == 0.95

    assert remaining_docs[1]["title"] == "記事3"
    assert remaining_docs[1]["personalized"]["rank"] == 2, "doc3のrankは2であるべき（DBは3だが表示用に再割当て）"
    assert pytest.approx(remaining_docs[1]["personalized"]["score"], rel=1e-3) == 0.75

    assert remaining_docs[2]["title"] == "記事5"
    assert remaining_docs[2]["personalized"]["rank"] == 3, "doc5のrankは3であるべき（DBは5だが表示用に再割当て）"
    assert pytest.approx(remaining_docs[2]["personalized"]["score"], rel=1e-3) == 0.55
