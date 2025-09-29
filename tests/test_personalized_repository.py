from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.core.database import Document, PersonalizedScore, SessionLocal, create_tables
from app.services.personalization_models import ExplanationBreakdown, PersonalizedScoreDTO
from app.services.personalized_repository import PersonalizedScoreRepository


@pytest.fixture()
def db_session():
	create_tables()
	session = SessionLocal()
	# Keep tests isolated by clearing personalized_scores before running assertions
	session.query(PersonalizedScore).delete()
	session.commit()
	try:
		yield session
	finally:
		session.query(PersonalizedScore).delete()
		session.commit()
		session.close()


def _create_document(session, *, doc_id: str) -> Document:
	doc = Document(
		id=doc_id,
		url=f"https://example.com/{doc_id}",
		domain="example.com",
		title=f"Document {doc_id}",
		content_md="# sample",
		content_text="sample text",
		hash=f"hash-{doc_id}",
	)
	session.add(doc)
	session.commit()
	return doc


def test_bulk_upsert_creates_and_updates_scores(db_session):
	repo = PersonalizedScoreRepository(db_session)
	doc_a = _create_document(db_session, doc_id="doc-a")
	doc_b = _create_document(db_session, doc_id="doc-b")
	created_at = datetime.utcnow().replace(microsecond=0)

	initial_scores = [
		PersonalizedScoreDTO(
			id=str(uuid.uuid4()),
			document_id=doc_a.id,
			score=0.8,
			rank=1,
			components=ExplanationBreakdown(similarity=0.9, category=0.4, domain=0.3, freshness=0.95),
			explanation="強いマッチ",
			computed_at=created_at,
			user_id="user-1",
			cold_start=False,
		),
		PersonalizedScoreDTO(
			id=str(uuid.uuid4()),
			document_id=doc_b.id,
			score=0.45,
			rank=2,
			components=ExplanationBreakdown(similarity=0.5, category=0.2, domain=0.1, freshness=0.75),
			explanation="平均的な一致",
			computed_at=created_at,
			user_id="user-1",
			cold_start=False,
		),
	]

	persisted_ids = repo.bulk_upsert(initial_scores, profile_id="profile-1", user_id="user-1")
	assert len(persisted_ids) == 2

	scores_after_insert = repo.list_scores(user_id="user-1", limit=10)
	assert [score.document_id for score in scores_after_insert] == [doc_a.id, doc_b.id]
	assert scores_after_insert[0].components.similarity == pytest.approx(0.9)
	assert scores_after_insert[0].cold_start is False

	updated_scores = [
		PersonalizedScoreDTO(
			id=initial_scores[0].id,
			document_id=doc_a.id,
			score=0.92,
			rank=1,
			components=ExplanationBreakdown(similarity=0.95, category=0.7, domain=0.35, freshness=0.98),
			explanation="更新後のマッチ",
			computed_at=created_at + timedelta(minutes=15),
			user_id="user-1",
			cold_start=True,
		),
	]

	repo.bulk_upsert(updated_scores, profile_id="profile-1", user_id="user-1")

	score_map = {score.document_id: score for score in repo.list_scores(user_id="user-1", limit=10)}
	assert pytest.approx(score_map[doc_a.id].score, rel=1e-3) == 0.92
	assert score_map[doc_a.id].cold_start is True
	assert "更新後" in score_map[doc_a.id].explanation


def test_bulk_upsert_requires_single_user(db_session):
	repo = PersonalizedScoreRepository(db_session)
	doc = _create_document(db_session, doc_id="doc-conflict")
	created_at = datetime.utcnow()

	scores = [
		PersonalizedScoreDTO(
			id=str(uuid.uuid4()),
			document_id=doc.id,
			score=0.7,
			rank=1,
			components=ExplanationBreakdown(similarity=0.7, category=0.6, domain=0.4, freshness=0.8),
			explanation="ユーザー1",
			computed_at=created_at,
			user_id="user-1",
			cold_start=False,
		),
		PersonalizedScoreDTO(
			id=str(uuid.uuid4()),
			document_id=doc.id,
			score=0.6,
			rank=2,
			components=ExplanationBreakdown(similarity=0.6, category=0.3, domain=0.3, freshness=0.7),
			explanation="ユーザー2",
			computed_at=created_at,
			user_id="user-2",
			cold_start=False,
		),
	]

	with pytest.raises(ValueError):
		repo.bulk_upsert(scores, profile_id="profile-xyz")


def test_delete_and_map_scores(db_session):
	repo = PersonalizedScoreRepository(db_session)
	doc_a = _create_document(db_session, doc_id="doc-del-a")
	doc_b = _create_document(db_session, doc_id="doc-del-b")
	doc_c = _create_document(db_session, doc_id="doc-del-c")
	ts = datetime.utcnow()

	repo.bulk_upsert(
		[
			PersonalizedScoreDTO(
				id=str(uuid.uuid4()),
				document_id=doc_a.id,
				score=0.3,
				rank=3,
				components=ExplanationBreakdown(similarity=0.3, category=0.1, domain=0.2, freshness=0.5),
				explanation="A",
				computed_at=ts,
				user_id="user-map",
				cold_start=False,
			),
			PersonalizedScoreDTO(
				id=str(uuid.uuid4()),
				document_id=doc_b.id,
				score=0.6,
				rank=1,
				components=ExplanationBreakdown(similarity=0.7, category=0.2, domain=0.2, freshness=0.6),
				explanation="B",
				computed_at=ts,
				user_id="user-map",
				cold_start=False,
			),
			PersonalizedScoreDTO(
				id=str(uuid.uuid4()),
				document_id=doc_c.id,
				score=0.5,
				rank=2,
				components=ExplanationBreakdown(similarity=0.5, category=0.3, domain=0.2, freshness=0.4),
				explanation="C",
				computed_at=ts,
				user_id="user-map",
				cold_start=False,
			),
		],
		profile_id="profile-map",
	)

	mapping = repo.map_scores_for_documents(user_id="user-map", document_ids=[doc_a.id, doc_b.id, "missing"])
	assert set(mapping.keys()) == {doc_a.id, doc_b.id}
	assert mapping[doc_b.id].rank == 1

	deleted = repo.delete_scores(user_id="user-map", document_ids=[doc_a.id])
	assert deleted == 1

	remaining = repo.list_scores(user_id="user-map", limit=10)
	assert [score.document_id for score in remaining] == [doc_b.id, doc_c.id]