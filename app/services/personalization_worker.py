"""Background worker for processing preference jobs."""
from __future__ import annotations

import json
import logging
import time
from typing import Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy.orm import joinedload

from app.core.database import Document, PreferenceJob
from app.core import database as app_db
from app.services.personalization_queue import (
	DEFAULT_POLL_INTERVAL_SECONDS,
	lease_job,
	mark_job_done,
	mark_job_failed,
)
from app.services.personalized_ranking import PersonalizedRankingService
from app.services.personalized_repository import PersonalizedScoreRepository
from app.services.personalization_models import PersonalizedScoreDTO, PreferenceProfileDTO
from app.services.preference_profile import PreferenceProfileService
from app.core.user_utils import normalize_user_id

logger = logging.getLogger(__name__)

DEFAULT_DOCUMENT_LIMIT = 200


def _parse_payload(job: PreferenceJob) -> Dict[str, object]:
	if not job.payload:
		return {}
	try:
		data = json.loads(job.payload)
		if isinstance(data, dict):
			return data
		logger.warning("personalization_worker: job %s payload is not a dict", job.id)
		return {}
	except (TypeError, ValueError, json.JSONDecodeError):
		logger.warning("personalization_worker: failed to decode payload for job %s", job.id)
		return {}


def _resolve_target_ids(job: PreferenceJob, payload: Dict[str, object]) -> Set[str]:
	candidates: Set[str] = set()
	if job.document_id:
		candidates.add(str(job.document_id))
	docs = payload.get("document_ids")
	if isinstance(docs, Sequence) and not isinstance(docs, (str, bytes)):
		for value in docs:
			if value is not None:
				candidates.add(str(value))
	return candidates


def _load_documents(session, *, target_ids: Set[str], limit: int) -> List[Document]:
	query = session.query(Document).options(
		joinedload(Document.classifications),
		joinedload(Document.embeddings),
	)

	documents: Dict[str, Document] = {}

	if target_ids:
		target_rows = (
			query.filter(Document.id.in_(list(target_ids))).all()
		)
		for row in target_rows:
			documents[row.id] = row

	if len(documents) < limit:
		remaining = max(limit - len(documents), 0)
		if remaining:
			extra_rows = (
				query.order_by(Document.created_at.desc())
				.limit(limit)
				.all()
			)
			for row in extra_rows:
				if row.id not in documents:
					documents[row.id] = row
				if len(documents) >= limit:
					break

	return list(documents.values())


def _compute_scores(
	*,
	profile: PreferenceProfileDTO,
	documents: Sequence[Document],
	ranking_service: PersonalizedRankingService,
) -> List[PersonalizedScoreDTO]:
	return ranking_service.score_documents(documents, profile=profile)


def _handle_profile_rebuild(
	session,
	job: PreferenceJob,
	*,
	payload: Dict[str, object],
	profile_service: PreferenceProfileService,
	ranking_service: PersonalizedRankingService,
) -> Tuple[bool, Optional[str]]:
	profile = profile_service.update_profile(session, user_id=job.user_id)
	limit = int(payload.get("limit", DEFAULT_DOCUMENT_LIMIT) or DEFAULT_DOCUMENT_LIMIT)
	limit = max(min(limit, 500), 1)
	target_ids = _resolve_target_ids(job, payload)
	logger.info(
		"personalization_worker: processing job %s (type=%s user=%s target_docs=%s limit=%s)",
		job.id,
		job.job_type,
		job.user_id,
		target_ids or "ALL",
		limit,
	)
	documents = _load_documents(session, target_ids=target_ids, limit=limit)

	if target_ids and not documents:
		missing = ",".join(sorted(target_ids))
		logger.warning("personalization_worker: documents for job %s missing (%s)", job.id, missing)
		return False, f"missing-documents:{missing}"

	scores = _compute_scores(
		profile=profile,
		documents=documents,
		ranking_service=ranking_service,
	)

	repo = PersonalizedScoreRepository(session)
	persisted = repo.bulk_upsert(scores, profile_id=profile.id, user_id=profile.user_id)
	resolved_user = normalize_user_id(profile.user_id)
	logger.info(
		"personalization_worker: job %s stored %d scores for user=%s",
		job.id,
		len(persisted),
		resolved_user,
	)

	if not scores and target_ids:
		repo.delete_scores(user_id=profile.user_id, document_ids=list(target_ids))

	return True, None


def _process_job(
	session,
	job: PreferenceJob,
	*,
	profile_service: PreferenceProfileService,
	ranking_service: PersonalizedRankingService,
) -> Tuple[bool, Optional[str]]:
	payload = _parse_payload(job)

	job_type = (job.job_type or "profile_rebuild").strip().lower()
	if job_type in {"profile_rebuild", "score_refresh"}:
		return _handle_profile_rebuild(
			session,
			job,
			payload=payload,
			profile_service=profile_service,
			ranking_service=ranking_service,
		)

	logger.warning("personalization_worker: unsupported job type '%s' for job %s", job_type, job.id)
	return True, None


def run_worker(poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS) -> None:
	"""Run the preference worker loop indefinitely."""

	logger.info("Starting preference worker with poll interval %.2fs", poll_interval)
	profile_service = PreferenceProfileService()
	ranking_service = PersonalizedRankingService()

	while True:
		session = app_db.SessionLocal()
		try:
			job = lease_job(session)
			if not job:
				time.sleep(poll_interval)
				continue

			success, error = _process_job(
				session,
				job,
				profile_service=profile_service,
				ranking_service=ranking_service,
			)
			if success:
				mark_job_done(session, job)
			else:
				mark_job_failed(session, job, error or "unknown error")
		except Exception:
			logger.exception("personalization_worker: unexpected error while processing job")
		finally:
			try:
				session.close()
			except Exception:
				pass


def run_once() -> None:
	"""Process a single job and exit (useful for tests)."""

	session = app_db.SessionLocal()
	try:
		job = lease_job(session)
		if not job:
			logger.info("personalization_worker: no jobs available for run_once")
			return

		profile_service = PreferenceProfileService()
		ranking_service = PersonalizedRankingService()
		success, error = _process_job(
			session,
			job,
			profile_service=profile_service,
			ranking_service=ranking_service,
		)
		if success:
			mark_job_done(session, job)
		else:
			mark_job_failed(session, job, error or "unknown error")
	finally:
		try:
			session.close()
		except Exception:
			pass


__all__ = ["run_worker", "run_once"]
