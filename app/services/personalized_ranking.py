from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple

from app.services.personalization_models import (
	ExplanationBreakdown,
	PersonalizedScoreDTO,
	PreferenceProfileDTO,
)
from app.services.similarity import cosine_similarity

logger = logging.getLogger(__name__)


def _clip_unit(value: float) -> float:
	return max(0.0, min(1.0, float(value)))


def _ensure_datetime(value: Any) -> Optional[datetime]:
	if value is None:
		return None
	if isinstance(value, datetime):
		return value
	if isinstance(value, str):
		# Try flexible parsing first (RFC 2822, timezones, etc.)
		try:
			from dateutil import parser as _dateutil_parser
			return _dateutil_parser.parse(value)
		except Exception:
			try:
				return datetime.fromisoformat(value)
			except Exception:
				return None
	return None


def _extract_primary_category(document: Any) -> Optional[str]:
	classifications = getattr(document, "classifications", None) or []
	for classification in classifications:
		primary = getattr(classification, "primary_category", None)
		if primary:
			return str(primary)
	return None


def _extract_embedding(document: Any) -> Tuple[float, ...]:
	embeddings = getattr(document, "embeddings", None)
	if embeddings:
		candidate = None
		for item in embeddings:
			vec_payload = getattr(item, "vec", None)
			if not vec_payload:
				continue
			chunk_id = getattr(item, "chunk_id", 0)
			if candidate is None or chunk_id < getattr(candidate, "chunk_id", 0):
				candidate = item
		if candidate:
			try:
				data = json.loads(candidate.vec)
				return tuple(float(x) for x in data)
			except (TypeError, ValueError, json.JSONDecodeError):
				logger.warning("personalized_ranking: failed to decode embedding payload for document %s", getattr(document, "id", "unknown"))
	payload = getattr(document, "embedding", None) or getattr(document, "embedding_vector", None)
	if payload:
		if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
			try:
				return tuple(float(x) for x in payload)
			except (TypeError, ValueError):
				return ()
		if isinstance(payload, str):
			try:
				data = json.loads(payload)
				return tuple(float(x) for x in data)
			except (TypeError, ValueError, json.JSONDecodeError):
				logger.warning("personalized_ranking: failed to parse string embedding for document %s", getattr(document, "id", "unknown"))
	return ()


def _hours_between(later: datetime, earlier: datetime) -> float:
	def _to_utc(value: datetime) -> datetime:
		if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
			return value.replace(tzinfo=timezone.utc)
		return value.astimezone(timezone.utc)

	try:
		later_utc = _to_utc(later)
		ear_utc = _to_utc(earlier)
		delta = later_utc - ear_utc
	except Exception:
		try:
			delta = (later.replace(tzinfo=None) - earlier.replace(tzinfo=None))
		except Exception:
			return 0.0
	return max(delta.total_seconds() / 3600.0, 0.0)


class ExplanationPresenter:
	"""日本語で説明文を生成するヘルパー。"""

	def __init__(
		self,
		*,
		joiner: str = " / ",
		strong_threshold: float = 0.65,
		medium_threshold: float = 0.35,
		fresh_threshold: float = 0.5,
	):
		self.joiner = joiner
		self.strong_threshold = strong_threshold
		self.medium_threshold = medium_threshold
		self.fresh_threshold = fresh_threshold

	def render(
		self,
		document: Any,
		breakdown: ExplanationBreakdown,
		*,
		profile: Optional[PreferenceProfileDTO],
		cold_start: bool,
	) -> str:
		parts: List[str] = []

		if cold_start:
			parts.append("ブックマークがまだ少ないため暫定的なおすすめです。")

		primary_category = _extract_primary_category(document)
		domain = getattr(document, "domain", None)

		if breakdown.similarity >= self.strong_threshold:
			parts.append("内容が最近の関心と強く一致しています。")
		elif breakdown.similarity >= self.medium_threshold:
			parts.append("内容があなたの興味とおおむね合致しています。")
		else:
			parts.append("内容の一致度はまだ低めです。")

		if primary_category:
			if breakdown.category >= self.medium_threshold:
				parts.append(f"{primary_category} 分野の記事をよく読んでいるため優先しました。")
			elif breakdown.category <= 0.1:
				parts.append(f"{primary_category} 分野はこれから学習していきます。")

		if domain:
			if breakdown.domain >= self.medium_threshold:
				parts.append(f"{domain} のコンテンツを頻繁に保存している傾向があります。")
			elif breakdown.domain <= 0.1:
				parts.append(f"{domain} からの情報はまだ少なめです。")

		if breakdown.freshness >= self.fresh_threshold:
			parts.append("新着の記事なので早めにチェックすると良いでしょう。")
		else:
			parts.append("更新から少し時間が経っています。")

		if breakdown.note:
			parts.append(breakdown.note)

		if profile and profile.is_cold_start:
			parts.append("今後のブックマークで精度が向上します。")

		return self.joiner.join(part for part in parts if part).strip()


class PersonalizedRankingService:
	"""プロファイルとドキュメント群から個別スコアを算出するサービス。"""

	def __init__(
		self,
		*,
		similarity_weight: float = 0.5,
		category_weight: float = 0.25,
		domain_weight: float = 0.15,
		freshness_weight: float = 0.1,
		now_provider: Optional[Callable[[], datetime]] = None,
		explanation_presenter: Optional[ExplanationPresenter] = None,
	):
		total = similarity_weight + category_weight + domain_weight + freshness_weight
		if total <= 0:
			raise ValueError("at least one component weight must be positive")
		self.similarity_weight = similarity_weight / total
		self.category_weight = category_weight / total
		self.domain_weight = domain_weight / total
		self.freshness_weight = freshness_weight / total
		self._now_provider = now_provider or datetime.utcnow
		self.presenter = explanation_presenter or ExplanationPresenter()

	def score_documents(
		self,
		documents: Sequence[Any],
		*,
		profile: Optional[PreferenceProfileDTO] = None,
	) -> List[PersonalizedScoreDTO]:
		if not documents:
			return []

		now = self._now_provider()
		profile_embedding = tuple(profile.embedding) if profile else ()
		category_weights = dict(profile.category_weights) if profile else {}
		domain_weights = dict(profile.domain_weights) if profile else {}
		cold_start = profile is None or profile.is_cold_start

		results: List[Tuple[PersonalizedScoreDTO, Any]] = []

		for document in documents:
			document_id = str(getattr(document, "id", ""))
			if not document_id:
				logger.debug("personalized_ranking: skipped document without id")
				continue

			embedding = _extract_embedding(document)
			similarity = self._compute_similarity(profile_embedding, embedding)

			primary_category = _extract_primary_category(document)
			category_score = _clip_unit(category_weights.get(primary_category, 0.0) if primary_category else 0.0)

			domain = getattr(document, "domain", None)
			domain_score = _clip_unit(domain_weights.get(str(domain), 0.0) if domain else 0.0)

			freshness = self._compute_freshness(now, document)

			breakdown = ExplanationBreakdown(
				similarity=similarity,
				category=category_score,
				domain=domain_score,
				freshness=freshness,
			)

			score = self._compose_score(breakdown)

			explanation = self.presenter.render(
				document,
				breakdown,
				profile=profile,
				cold_start=cold_start,
			)

			dto = PersonalizedScoreDTO(
				id=str(uuid.uuid4()),
				document_id=document_id,
				score=score,
				rank=0,
				components=breakdown,
				explanation=explanation,
				computed_at=now,
				user_id=profile.user_id if profile else None,
				cold_start=cold_start,
			)
			results.append((dto, document))

		if not results:
			return []

		results.sort(
			key=lambda item: (
				-item[0].score,
				self._freshness_sort_key(item[1]),
				item[0].document_id,
			)
		)

		ordered: List[PersonalizedScoreDTO] = []
		for index, (dto, _) in enumerate(results, start=1):
			ordered.append(dto.with_rank(index).clamp_score())
		return ordered

	def _compute_similarity(
		self,
		profile_embedding: Sequence[float],
		doc_embedding: Sequence[float],
	) -> float:
		if not profile_embedding or not doc_embedding:
			return 0.0
		length = min(len(profile_embedding), len(doc_embedding))
		if length == 0:
			return 0.0
		vec1 = [float(x) for x in profile_embedding[:length]]
		vec2 = [float(x) for x in doc_embedding[:length]]
		try:
			return _clip_unit(cosine_similarity(vec1, vec2))
		except Exception:
			logger.exception("personalized_ranking: similarity computation failed")
			return 0.0

	def _compute_freshness(self, now: datetime, document: Any) -> float:
		candidates: Iterable[Any] = (
			getattr(document, "published_at", None),
			getattr(document, "created_at", None),
			getattr(document, "updated_at", None),
			getattr(document, "fetched_at", None),
		)
		for candidate in candidates:
			ts = _ensure_datetime(candidate)
			if ts:
				hours = _hours_between(now, ts)
				return _clip_unit(math.exp(-hours / 72.0))
		return 0.2

	def _compose_score(self, breakdown: ExplanationBreakdown) -> float:
		value = (
			self.similarity_weight * breakdown.similarity
			+ self.category_weight * breakdown.category
			+ self.domain_weight * breakdown.domain
			+ self.freshness_weight * breakdown.freshness
		)
		return _clip_unit(value)

	def _freshness_sort_key(self, document: Any) -> float:
		ts = _ensure_datetime(getattr(document, "created_at", None))
		if not ts:
			ts = _ensure_datetime(getattr(document, "updated_at", None))
		if not ts:
			ts = _ensure_datetime(getattr(document, "published_at", None))
		if not ts:
			ts = _ensure_datetime(getattr(document, "fetched_at", None))
		if not ts:
			return float("inf")
		return -ts.timestamp()


__all__ = ["PersonalizedRankingService", "ExplanationPresenter"]
