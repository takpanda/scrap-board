import json
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

import pytest

from app.services.personalization_models import PreferenceProfileDTO
from app.services.personalized_ranking import PersonalizedRankingService


class FakeEmbedding:
	def __init__(self, vec: Sequence[float], *, chunk_id: int = 0):
		self.vec = json.dumps([float(x) for x in vec])
		self.chunk_id = chunk_id


class FakeClassification:
	def __init__(self, primary_category: Optional[str]):
		self.primary_category = primary_category


class FakeDocument:
	def __init__(
		self,
		*,
		doc_id: str,
		embedding: Optional[Sequence[float]] = None,
		category: Optional[str] = None,
		domain: Optional[str] = None,
		created_at: Optional[datetime] = None,
	):
		self.id = doc_id
		self.embeddings = []
		if embedding is not None:
			self.embeddings = [FakeEmbedding(embedding)]
		self.classifications = []
		if category:
			self.classifications = [FakeClassification(category)]
		self.domain = domain
		ts = created_at or datetime.utcnow()
		self.created_at = ts
		self.updated_at = ts
		self.published_at = ts
		self.fetched_at = ts
		self.title = f"Document {doc_id}"


@pytest.fixture
def now() -> datetime:
	return datetime.utcnow().replace(microsecond=0)


def test_score_documents_prioritizes_strong_matches(now: datetime):
	service = PersonalizedRankingService(now_provider=lambda: now)
	profile = PreferenceProfileDTO(
		id="profile-1",
		user_id="user-1",
		bookmark_count=6,
		embedding=(0.25, 0.25, 0.25, 0.25),
		category_weights={"テック/AI": 0.7},
		domain_weights={"tech.example": 0.8},
		last_bookmark_id=None,
		status="active",
		created_at=now,
		updated_at=now,
	)
	doc_strong = FakeDocument(
		doc_id="doc-strong",
		embedding=[0.25, 0.25, 0.25, 0.25],
		category="テック/AI",
		domain="tech.example",
		created_at=now - timedelta(hours=1),
	)
	doc_weak = FakeDocument(
		doc_id="doc-weak",
		embedding=[0.0, 0.0, 0.0, 0.0],
		category="ビジネス",
		domain="biz.example",
		created_at=now - timedelta(hours=240),
	)

	scores = service.score_documents([doc_weak, doc_strong], profile=profile)

	assert [score.document_id for score in scores] == ["doc-strong", "doc-weak"]
	assert scores[0].rank == 1
	assert scores[1].rank == 2

	expected_freshness = math.exp(-1 / 72.0)
	expected_score = (
		0.5 * 1.0
		+ 0.25 * 0.7
		+ 0.15 * 0.8
		+ 0.1 * expected_freshness
	)
	assert pytest.approx(scores[0].score, rel=1e-3) == expected_score
	assert pytest.approx(scores[0].components.similarity, rel=1e-6) == 1.0
	assert pytest.approx(scores[0].components.category, rel=1e-6) == 0.7
	assert pytest.approx(scores[0].components.domain, rel=1e-6) == 0.8
	assert pytest.approx(scores[0].components.freshness, rel=1e-6) == expected_freshness
	assert scores[0].explanation

	expected_freshness_weak = math.exp(-240 / 72.0)
	expected_score_weak = 0.1 * expected_freshness_weak
	assert pytest.approx(scores[1].score, rel=1e-3) == expected_score_weak


def test_score_documents_marks_cold_start(now: datetime):
	service = PersonalizedRankingService(now_provider=lambda: now)
	profile = PreferenceProfileDTO(
		id="profile-cold",
		user_id=None,
		bookmark_count=1,
		embedding=(),
		category_weights={},
		domain_weights={},
		last_bookmark_id=None,
		status="cold_start",
		created_at=now,
		updated_at=now,
	)
	doc = FakeDocument(doc_id="doc-1", embedding=None, category=None, domain=None, created_at=now - timedelta(hours=12))

	scores = service.score_documents([doc], profile=profile)

	assert len(scores) == 1
	assert scores[0].cold_start is True
	assert "暫定" in scores[0].explanation


def test_score_documents_uses_category_and_domain_weights(now: datetime):
	service = PersonalizedRankingService(now_provider=lambda: now)
	profile = PreferenceProfileDTO(
		id="profile-weights",
		user_id="user-weights",
		bookmark_count=5,
		embedding=(),
		category_weights={"ビジネス": 0.5},
		domain_weights={"biz.example": 0.4},
		last_bookmark_id=None,
		status="active",
		created_at=now,
		updated_at=now,
	)
	doc = FakeDocument(
		doc_id="doc-biz",
		embedding=None,
		category="ビジネス",
		domain="biz.example",
		created_at=now - timedelta(hours=2),
	)

	scores = service.score_documents([doc], profile=profile)

	expected_freshness = math.exp(-2 / 72.0)
	expected_score = 0.25 * 0.5 + 0.15 * 0.4 + 0.1 * expected_freshness
	assert pytest.approx(scores[0].score, rel=1e-3) == expected_score
	assert pytest.approx(scores[0].components.category, rel=1e-6) == 0.5
	assert pytest.approx(scores[0].components.domain, rel=1e-6) == 0.4
	assert pytest.approx(scores[0].components.similarity, rel=1e-6) == 0.0
	assert pytest.approx(scores[0].components.freshness, rel=1e-6) == expected_freshness


def test_score_documents_handles_timezone_aware_datetimes(now: datetime):
	aware_now = datetime.now(timezone.utc)
	service = PersonalizedRankingService(now_provider=lambda: aware_now.replace(tzinfo=None))
	profile = PreferenceProfileDTO(
		id="profile-tz",
		user_id=None,
		bookmark_count=5,
		embedding=(),
		category_weights={},
		domain_weights={"tz.example": 1.0},
		last_bookmark_id=None,
		status="active",
		created_at=aware_now,
		updated_at=aware_now,
	)
	doc = FakeDocument(
		doc_id="doc-tz",
		embedding=None,
		category=None,
		domain="tz.example",
		created_at=aware_now - timedelta(hours=6),
	)
	# Ensure at least one timestamp remains timezone-aware
	doc.updated_at = (aware_now - timedelta(hours=6)).astimezone(timezone.utc)
	doc.fetched_at = (aware_now - timedelta(hours=6)).astimezone(timezone.utc)

	scores = service.score_documents([doc], profile=profile)

	assert len(scores) == 1
	assert scores[0].document_id == "doc-tz"
	assert scores[0].components.freshness > 0