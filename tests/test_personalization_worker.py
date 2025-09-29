from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.database import Document, PersonalizedScore, PreferenceJob, create_tables
from app.core import database as app_db
from app.services.personalization_models import ExplanationBreakdown, PersonalizedScoreDTO, PreferenceProfileDTO
from app.services.personalization_queue import enqueue_profile_update
from app.services import personalization_worker as worker


@pytest.fixture()
def db_session():
    create_tables()
    session = app_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _persist_document(session: Session, *, title: str) -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        url=f"https://example.com/{uuid.uuid4()}",
        domain="example.com",
        title=title,
        content_md="# heading\nbody",
        content_text="body",
        hash=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def test_run_once_processes_profile_rebuild(monkeypatch, db_session):
    document = _persist_document(db_session, title="スコア対象")
    job_id = enqueue_profile_update(db_session, user_id="user-abc", document_id=document.id)

    profile_dto = PreferenceProfileDTO(
        id="profile-abc",
        user_id="user-abc",
        bookmark_count=5,
        embedding=(0.1, 0.2, 0.3),
        category_weights={"テック/AI": 0.8},
        domain_weights={"example.com": 0.6},
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    score_dto = PersonalizedScoreDTO(
        id=str(uuid.uuid4()),
        document_id=document.id,
        score=0.88,
        rank=1,
        components=ExplanationBreakdown(similarity=0.9, category=0.7, domain=0.4, freshness=0.8),
        explanation="最近のブックマークに近い内容です。",
        computed_at=datetime.utcnow(),
        user_id="user-abc",
        cold_start=False,
    )

    captured = {}

    class FakeProfileService:
        def update_profile(self, session, user_id=None):
            captured["profile_user"] = user_id
            return profile_dto

    class FakeRankingService:
        def score_documents(self, documents, profile=None):
            captured["scored_ids"] = [doc.id for doc in documents]
            captured["profile"] = profile
            return [score_dto]

    monkeypatch.setattr(worker, "PreferenceProfileService", lambda: FakeProfileService())
    monkeypatch.setattr(worker, "PersonalizedRankingService", lambda: FakeRankingService())

    worker.run_once()

    refreshed = app_db.SessionLocal()
    try:
        job = refreshed.query(PreferenceJob).filter_by(id=job_id).first()
        assert job is not None
        assert job.status == "done"

        saved_scores = refreshed.query(PersonalizedScore).filter_by(document_id=document.id, user_id="user-abc").all()
        assert len(saved_scores) == 1
        assert pytest.approx(saved_scores[0].score, rel=1e-3) == 0.88
        assert captured["profile_user"] == "user-abc"
        assert captured["scored_ids"] == [document.id]
        assert captured["profile"].id == profile_dto.id
    finally:
        refreshed.close()


def test_run_once_marks_job_failed_when_no_documents(monkeypatch, db_session):
    job_id = enqueue_profile_update(db_session, user_id="user-missing", document_id="missing-doc")

    profile_dto = PreferenceProfileDTO(
        id="profile-missing",
        user_id="user-missing",
        bookmark_count=5,
        embedding=(),
        category_weights={},
        domain_weights={},
        status="cold_start",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    class FakeProfileService:
        def update_profile(self, session, user_id=None):
            return profile_dto

    class FakeRankingService:
        def score_documents(self, documents, profile=None):
            return []

    monkeypatch.setattr(worker, "PreferenceProfileService", lambda: FakeProfileService())
    monkeypatch.setattr(worker, "PersonalizedRankingService", lambda: FakeRankingService())

    worker.run_once()

    refreshed = app_db.SessionLocal()
    try:
        job = refreshed.query(PreferenceJob).filter_by(id=job_id).first()
        assert job is not None
        assert job.status in {"failed", "pending"}
        assert job.attempts >= 1
        assert refreshed.query(PersonalizedScore).count() == 0
    finally:
        refreshed.close()


def test_run_once_requeues_failed_job_with_backoff(monkeypatch, db_session):
    job_id = enqueue_profile_update(
        db_session,
        user_id="user-retry",
        document_id="missing-retry",
        max_attempts=2,
    )

    profile_dto = PreferenceProfileDTO(
        id="profile-retry",
        user_id="user-retry",
        bookmark_count=1,
        embedding=(),
        category_weights={},
        domain_weights={},
        status="cold_start",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    class FakeProfileService:
        def update_profile(self, session, user_id=None):
            return profile_dto

    class FakeRankingService:
        def score_documents(self, documents, profile=None):
            return []

    monkeypatch.setattr(worker, "PreferenceProfileService", lambda: FakeProfileService())
    monkeypatch.setattr(worker, "PersonalizedRankingService", lambda: FakeRankingService())

    worker.run_once()

    refreshed = app_db.SessionLocal()
    try:
        job = refreshed.query(PreferenceJob).filter_by(id=job_id).first()
        assert job is not None
        assert job.status == "pending"
        assert job.attempts == 1
        assert job.last_error is not None and "missing-documents" in job.last_error
        assert job.next_attempt_at is not None
        assert job.next_attempt_at > datetime.utcnow()
        scheduled_retry = job.next_attempt_at

        resume_time = datetime.utcnow() - timedelta(seconds=1)
        job.next_attempt_at = resume_time
        refreshed.add(job)
        refreshed.commit()
    finally:
        refreshed.close()

    worker.run_once()

    verify = app_db.SessionLocal()
    try:
        job = verify.query(PreferenceJob).filter_by(id=job_id).first()
        assert job is not None
        assert job.status == "failed"
        assert job.attempts == 2
        assert job.last_error is not None and "missing-documents" in job.last_error
        assert job.next_attempt_at is not None
        assert job.next_attempt_at >= scheduled_retry or job.next_attempt_at >= resume_time
        assert abs((job.next_attempt_at - resume_time).total_seconds()) < 0.5
    finally:
        verify.close()
