from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session, joinedload

from app.core.database import PersonalizedScore
from app.services.personalization_models import ExplanationBreakdown, PersonalizedScoreDTO

logger = logging.getLogger(__name__)


def _encode_components(dto: PersonalizedScoreDTO) -> str:
	payload = dto.components.to_dict()
	payload["__cold_start"] = bool(dto.cold_start)
	return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _decode_components(payload: Optional[str]) -> tuple[ExplanationBreakdown, bool]:
	if not payload:
		return ExplanationBreakdown(), False
	try:
		data = json.loads(payload)
	except (TypeError, ValueError, json.JSONDecodeError):
		logger.warning("personalized_repository: failed to decode components payload")
		return ExplanationBreakdown(), False

	cold_start = bool(data.pop("__cold_start", False))
	try:
		breakdown = ExplanationBreakdown.from_dict(data)
	except Exception:
		logger.exception("personalized_repository: failed to construct ExplanationBreakdown")
		breakdown = ExplanationBreakdown()
	return breakdown, cold_start


def _resolved_user_ids(scores: Sequence[PersonalizedScoreDTO], fallback_user_id: Optional[str]) -> Dict[Optional[str], List[PersonalizedScoreDTO]]:
	grouped: Dict[Optional[str], List[PersonalizedScoreDTO]] = {}
	for score in scores:
		resolved = score.user_id if score.user_id is not None else fallback_user_id
		if resolved not in grouped:
			grouped[resolved] = []
		grouped[resolved].append(score)
	return grouped


class PersonalizedScoreRepository:
	"""Repository utilities for personalized_scores table."""

	def __init__(self, session: Session):
		self.session = session

	def bulk_upsert(
		self,
		scores: Sequence[PersonalizedScoreDTO],
		*,
		profile_id: Optional[str],
		user_id: Optional[str] = None,
		commit: bool = True,
	) -> List[str]:
		"""Insert or update personalized scores in bulk.

		All scores must resolve to the same user_id after applying the optional
		explicit `user_id`. If a row already exists for a (user_id, document_id)
		pair, it will be updated; otherwise a new row is inserted. Returns the list
		of row IDs persisted.
		"""

		if not scores:
			return []

		grouped = _resolved_user_ids(scores, user_id)
		if len(grouped) != 1:
			raise ValueError("bulk_upsert requires all scores to resolve to the same user_id")

		resolved_user_id = next(iter(grouped))
		target_scores = grouped[resolved_user_id]
		document_ids = [score.document_id for score in target_scores]
		existing_query = self.session.query(PersonalizedScore).filter(PersonalizedScore.document_id.in_(document_ids))
		if resolved_user_id is None:
			existing_query = existing_query.filter(PersonalizedScore.user_id == None)  # noqa: E711
		else:
			existing_query = existing_query.filter(PersonalizedScore.user_id == resolved_user_id)

		existing_rows = {row.document_id: row for row in existing_query.all()}
		persisted_ids: List[str] = []
		now = datetime.utcnow()

		for score in target_scores:
			payload = _encode_components(score)
			row = existing_rows.get(score.document_id)
			if row:
				row.score = float(score.score)
				row.rank = int(score.rank)
				row.components = payload
				row.explanation = score.explanation
				row.computed_at = score.computed_at
				row.updated_at = now
				if profile_id is not None:
					row.profile_id = profile_id
				row.user_id = resolved_user_id
				persisted_ids.append(row.id)
			else:
				row_id = score.id or str(uuid.uuid4())
				row = PersonalizedScore(
					id=row_id,
					profile_id=profile_id,
					user_id=resolved_user_id,
					document_id=score.document_id,
					score=float(score.score),
					rank=int(score.rank),
					components=payload,
					explanation=score.explanation,
					computed_at=score.computed_at,
					created_at=now,
					updated_at=now,
				)
				self.session.add(row)
				persisted_ids.append(row_id)

		self.session.flush()
		if commit:
			self.session.commit()
		return persisted_ids

	def list_scores(
		self,
		*,
		user_id: Optional[str],
		limit: int = 20,
		offset: int = 0,
		with_documents: bool = False,
	) -> List[PersonalizedScoreDTO]:
		"""Retrieve ordered scores for a user."""

		if limit <= 0:
			return []

		query = self.session.query(PersonalizedScore)
		if with_documents:
			query = query.options(joinedload(PersonalizedScore.document))

		if user_id is None:
			query = query.filter(PersonalizedScore.user_id == None)  # noqa: E711
		else:
			query = query.filter(PersonalizedScore.user_id == user_id)

		rows = (
			query.order_by(PersonalizedScore.rank.asc(), PersonalizedScore.score.desc(), PersonalizedScore.document_id.asc())
			.offset(max(offset, 0))
			.limit(limit)
			.all()
		)
		return [self._row_to_dto(row) for row in rows]

	def map_scores_for_documents(
		self,
		*,
		user_id: Optional[str],
		document_ids: Sequence[str],
	) -> Dict[str, PersonalizedScoreDTO]:
		"""Return a mapping of document_id -> DTO for the given user."""

		if not document_ids:
			return {}

		query = self.session.query(PersonalizedScore).filter(PersonalizedScore.document_id.in_(list(document_ids)))
		if user_id is None:
			query = query.filter(PersonalizedScore.user_id == None)  # noqa: E711
		else:
			query = query.filter(PersonalizedScore.user_id == user_id)

		rows = query.all()
		return {row.document_id: self._row_to_dto(row) for row in rows}

	def delete_scores(
		self,
		*,
		user_id: Optional[str],
		document_ids: Optional[Sequence[str]] = None,
		commit: bool = True,
	) -> int:
		"""Delete personalized scores for a user. Returns number of rows removed."""

		query = self.session.query(PersonalizedScore)
		if user_id is None:
			query = query.filter(PersonalizedScore.user_id == None)  # noqa: E711
		else:
			query = query.filter(PersonalizedScore.user_id == user_id)

		if document_ids:
			query = query.filter(PersonalizedScore.document_id.in_(list(document_ids)))

		count = query.delete(synchronize_session=False)
		if commit:
			self.session.commit()
		return int(count)

	@staticmethod
	def _row_to_dto(row: PersonalizedScore) -> PersonalizedScoreDTO:
		breakdown, cold_start = _decode_components(row.components)
		computed_at = row.computed_at or row.updated_at or datetime.utcnow()
		return PersonalizedScoreDTO(
			id=row.id,
			document_id=row.document_id,
			score=float(row.score),
			rank=int(row.rank),
			components=breakdown,
			explanation=row.explanation or "",
			computed_at=computed_at,
			user_id=row.user_id,
			cold_start=cold_start,
		)


__all__ = ["PersonalizedScoreRepository"]
