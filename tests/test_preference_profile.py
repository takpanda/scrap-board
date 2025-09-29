import json
import uuid
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

import pytest
from sqlalchemy import text

from app.core.database import (
    Bookmark,
    Classification,
    Document,
    PreferenceProfile,
    SessionLocal,
    create_tables,
)
from app.services.preference_profile import PreferenceProfileService


class StaticEmbeddingLLM:
    """Test double that returns predefined embedding vectors."""

    def __init__(self, embeddings: Iterable[List[float]]):
        self._sequence = list(embeddings)
        if not self._sequence:
            self._sequence = [[0.0, 0.0, 0.0]]
        self.calls = 0

    async def create_embedding(self, text: str) -> Optional[List[float]]:  # pragma: no cover - async wrapper
        if self.calls < len(self._sequence):
            result = self._sequence[self.calls]
        else:
            result = self._sequence[-1]
        self.calls += 1
        return result


class FailingLLM:
    """Test double that always fails to produce embeddings."""

    def __init__(self):
        self.calls = 0

    async def create_embedding(self, text: str) -> Optional[List[float]]:  # pragma: no cover - async wrapper
        self.calls += 1
        return None


@pytest.fixture(autouse=True)
def _ensure_schema():
    create_tables()
    yield


def _reset_db() -> None:
    with SessionLocal() as db:
        for table in [
            "personalized_scores",
            "preference_jobs",
            "preference_feedbacks",
            "bookmarks",
            "classifications",
            "documents",
            "preference_profiles",
        ]:
            try:
                db.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass
        db.commit()


def _seed_bookmark(
    *,
    user_id: Optional[str],
    title: str,
    domain: str,
    category: str,
    note: Optional[str] = None,
    minutes_ago: int = 0,
) -> str:
    with SessionLocal() as db:
        now = datetime.utcnow() - timedelta(minutes=minutes_ago)
        doc = Document(
            id=str(uuid.uuid4()),
            url=f"http://example.test/{uuid.uuid4()}",
            domain=domain,
            title=title,
            content_md=f"## {title}\nコンテンツ",
            content_text=f"{title} に関する本文",
            hash=str(uuid.uuid4()),
            short_summary=f"{title}の要約",
            created_at=now,
            updated_at=now,
        )
        db.add(doc)
        db.flush()

        classification = Classification(
            document_id=doc.id,
            primary_category=category,
            topics=[],
            tags=[],
            confidence=0.9,
            method="test",
            created_at=now,
        )
        db.add(classification)

        bookmark = Bookmark(
            user_id=user_id,
            document_id=doc.id,
            note=note,
            created_at=now,
        )
        db.add(bookmark)
        db.commit()
        return bookmark.id


def test_update_profile_marks_cold_start_when_bookmarks_insufficient():
    _reset_db()
    user_id = "user-cold"
    _seed_bookmark(user_id=user_id, title="Doc1", domain="cold.example", category="テック/AI", minutes_ago=5)
    _seed_bookmark(user_id=user_id, title="Doc2", domain="cold.example", category="ビジネス", minutes_ago=4)

    service = PreferenceProfileService(llm=StaticEmbeddingLLM([[0.1, 0.2, 0.3]]), cold_start_threshold=3)
    with SessionLocal() as db:
        profile = service.update_profile(db, user_id=user_id)
        assert profile.status == "cold_start"
        assert profile.bookmark_count == 2
        assert profile.embedding == ()
        assert profile.category_weights == {}
        stored = db.query(PreferenceProfile).filter(PreferenceProfile.user_id == user_id).one()
        assert stored.profile_embedding is None
        assert stored.status == "cold_start"


def test_update_profile_generates_embedding_and_weights():
    _reset_db()
    user_id = "user-active"
    _seed_bookmark(user_id=user_id, title="AIニュース", domain="tech.example", category="テック/AI", minutes_ago=3)
    latest_id = _seed_bookmark(
        user_id=user_id,
        title="ビジネス分析",
        domain="biz.example",
        category="ビジネス",
        minutes_ago=1,
    )
    _seed_bookmark(user_id=user_id, title="AI市場動向", domain="tech.example", category="テック/AI", minutes_ago=2)

    service = PreferenceProfileService(llm=StaticEmbeddingLLM([[0.2, 0.4, 0.6]]), cold_start_threshold=3)
    with SessionLocal() as db:
        profile = service.update_profile(db, user_id=user_id)
        assert profile.status == "active"
        assert profile.bookmark_count == 3
        assert profile.embedding == (0.2, 0.4, 0.6)
        assert pytest.approx(profile.category_weights["テック/AI"], rel=1e-3) == 2 / 3
        assert pytest.approx(profile.category_weights["ビジネス"], rel=1e-3) == 1 / 3
        assert pytest.approx(profile.domain_weights["tech.example"], rel=1e-3) == 2 / 3
        assert pytest.approx(profile.domain_weights["biz.example"], rel=1e-3) == 1 / 3
        assert profile.last_bookmark_id == latest_id


def test_update_profile_preserves_embedding_when_generation_fails():
    _reset_db()
    user_id = "user-error"
    _seed_bookmark(user_id=user_id, title="AIニュース", domain="tech.example", category="テック/AI", minutes_ago=5)
    _seed_bookmark(user_id=user_id, title="市場分析", domain="biz.example", category="ビジネス", minutes_ago=3)
    _seed_bookmark(user_id=user_id, title="AI市場動向", domain="tech.example", category="テック/AI", minutes_ago=1)

    initial_service = PreferenceProfileService(llm=StaticEmbeddingLLM([[0.5, 0.6, 0.7]]))
    with SessionLocal() as db:
        initial_profile = initial_service.update_profile(db, user_id=user_id)
        assert initial_profile.status == "active"
        assert initial_profile.embedding == (0.5, 0.6, 0.7)

    failing_service = PreferenceProfileService(llm=FailingLLM(), max_retries=1, retry_delay_seconds=0.01)
    with SessionLocal() as db:
        profile = failing_service.update_profile(db, user_id=user_id)
        assert profile.status == "error"
        assert profile.embedding == (0.5, 0.6, 0.7)
        stored = db.query(PreferenceProfile).filter(PreferenceProfile.user_id == user_id).one()
        assert stored.status == "error"
        assert json.loads(stored.profile_embedding) == [0.5, 0.6, 0.7]