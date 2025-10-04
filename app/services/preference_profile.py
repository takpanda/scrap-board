from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session, joinedload

from app.core.database import Bookmark, Document, PreferenceProfile
from app.core.user_utils import normalize_user_id
from app.services.llm_client import LLMClient, llm_client
from app.services.personalization_models import PreferenceProfileDTO, PreferenceProfileStatus

logger = logging.getLogger(__name__)

# 暫定対応: 開発環境ではコールドスタート判定をやや緩めにする（3未満はコールドスタート扱い）
# モデル側の `PreferenceProfileDTO.is_cold_start` は bookmark_count < 3 もコールドスタートと見なすため
# デフォルト閾値を 3 に合わせます。
DEFAULT_COLD_START_THRESHOLD = 3
DEFAULT_MAX_BOOKMARKS = 50
DEFAULT_EMBEDDING_CHAR_LIMIT = 4000
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_DELAY_SECONDS = 1.5


def _normalize_status(value: Optional[str]) -> PreferenceProfileStatus:
	status = (value or "active").lower()
	if status in {"active", "cold_start", "error"}:
		return status  # type: ignore[return-value]
	if status == "ready":
		return "active"  # type: ignore[return-value]
	return "active"  # type: ignore[return-value]


def _loads_float_list(payload: Optional[str]) -> List[float]:
	if not payload:
		return []
	try:
		values = json.loads(payload)
	except (TypeError, ValueError, json.JSONDecodeError):
		logger.warning("preference_profile: failed to decode embedding payload")
		return []
	result: List[float] = []
	for item in values:
		try:
			result.append(float(item))
		except (TypeError, ValueError):
			continue
	return result


def _loads_float_map(payload: Optional[str]) -> Dict[str, float]:
	if not payload:
		return {}
	try:
		data = json.loads(payload)
	except (TypeError, ValueError, json.JSONDecodeError):
		logger.warning("preference_profile: failed to decode weight map")
		return {}
	result: Dict[str, float] = {}
	for key, value in data.items():
		try:
			result[str(key)] = float(value)
		except (TypeError, ValueError):
			continue
	return result


def _dumps(obj: Dict[str, float]) -> str:
	return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _run_async(coro_or_factory):
	"""Run an async coroutine safely even if an event loop is already running."""

	def _get_coro():
		if asyncio.iscoroutine(coro_or_factory):
			return coro_or_factory
		if callable(coro_or_factory):
			result = coro_or_factory()
			if asyncio.iscoroutine(result):
				return result
			raise TypeError("Callable must return a coroutine")
		raise TypeError("Expected coroutine or callable returning coroutine")

	try:
		loop = asyncio.get_running_loop()
	except RuntimeError:
		loop = None

	if loop and loop.is_running():
		container: Dict[str, object] = {}

		def _runner():
			try:
				container["value"] = asyncio.run(_get_coro())
			except Exception as exc:  # pragma: no cover - passthrough
				container["error"] = exc

		thread = threading.Thread(target=_runner, daemon=True)
		thread.start()
		thread.join()
		if "error" in container:
			raise container["error"]  # type: ignore[misc]
		return container.get("value")

	return asyncio.run(_get_coro())


class PreferenceProfileService:
	"""Service responsible for building and persisting preference profiles."""

	def __init__(
		self,
		llm: Optional[LLMClient] = None,
		cold_start_threshold: int = DEFAULT_COLD_START_THRESHOLD,
		max_bookmarks: int = DEFAULT_MAX_BOOKMARKS,
		embedding_char_limit: int = DEFAULT_EMBEDDING_CHAR_LIMIT,
		max_retries: int = DEFAULT_MAX_RETRIES,
		retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
	) -> None:
		if cold_start_threshold < 1:
			raise ValueError("cold_start_threshold must be >= 1")
		self.llm = llm or llm_client
		self.cold_start_threshold = cold_start_threshold
		self.max_bookmarks = max_bookmarks
		self.embedding_char_limit = embedding_char_limit
		self.max_retries = max_retries
		self.retry_delay_seconds = retry_delay_seconds

	def update_profile(self, db: Session, user_id: Optional[str] = None) -> PreferenceProfileDTO:
		bookmarks = self._load_recent_bookmarks(db, user_id)
		attached = [b for b in bookmarks if b.document is not None]
		bookmark_count = len(attached)
		last_bookmark_id = attached[0].id if attached else None

		profile = self._get_profile(db, user_id)
		if bookmark_count < self.cold_start_threshold:
			profile = self._persist_profile(
				db=db,
				profile=profile,
				user_id=user_id,
				bookmark_count=bookmark_count,
				last_bookmark_id=last_bookmark_id,
				status="cold_start",
				embedding=None,
				category_weights={},
				domain_weights={},
			)
			return self._to_dto(profile)

		category_weights = self._compute_category_weights(attached)
		domain_weights = self._compute_domain_weights(attached)
		embedding_text = self._compose_embedding_corpus(attached)
		embedding: Optional[List[float]] = None

		if embedding_text:
			embedding = self._generate_embedding(embedding_text)

		status: PreferenceProfileStatus
		if embedding:
			status = "active"  # type: ignore[assignment]
		else:
			status = "error"  # type: ignore[assignment]

		profile = self._persist_profile(
			db=db,
			profile=profile,
			user_id=user_id,
			bookmark_count=bookmark_count,
			last_bookmark_id=last_bookmark_id,
			status=status,
			embedding=embedding,
			category_weights=category_weights,
			domain_weights=domain_weights,
		)
		return self._to_dto(profile)

	def _generate_embedding(self, text: str) -> Optional[List[float]]:
		text = text.strip()
		if not text:
			return None
		last_error: Optional[str] = None
		for attempt in range(self.max_retries + 1):
			try:
				result = _run_async(lambda: self.llm.create_embedding(text))
				if result:
					return [float(x) for x in result]
			except Exception as exc:  # pragma: no cover - logging path
				last_error = str(exc)
				logger.exception(
					"preference_profile: embedding generation failed (attempt %s)",
					attempt + 1,
				)
			if attempt < self.max_retries:
				time.sleep(self.retry_delay_seconds)
		if last_error:
			logger.error("preference_profile: embedding generation failed permanently: %s", last_error)
		return None

	def _persist_profile(
		self,
		*,
		db: Session,
		profile: Optional[PreferenceProfile],
		user_id: Optional[str],
		bookmark_count: int,
		last_bookmark_id: Optional[str],
		status: PreferenceProfileStatus,
		embedding: Optional[Sequence[float]],
		category_weights: Dict[str, float],
		domain_weights: Dict[str, float],
	) -> PreferenceProfile:
		now = datetime.utcnow()
		# Normalize user_id to ensure we never persist NULL/empty user_id values
		normalized_user = normalize_user_id(user_id)
		if profile is None:
			profile = PreferenceProfile(
				id=str(uuid.uuid4()),
				user_id=normalized_user,
				created_at=now,
			)

		if embedding is not None:
			payload_embedding = json.dumps(list(embedding), ensure_ascii=False, separators=(",", ":"))
		elif status == "cold_start":
			payload_embedding = None
		else:
			payload_embedding = profile.profile_embedding

		payload_categories = _dumps(category_weights) if category_weights else "{}"
		payload_domains = _dumps(domain_weights) if domain_weights else "{}"

		# Ensure stored profile.user_id is normalized as well
		profile.user_id = normalize_user_id(user_id)
		profile.bookmark_count = bookmark_count
		profile.last_bookmark_id = last_bookmark_id
		profile.status = status
		profile.updated_at = now
		profile.profile_embedding = payload_embedding
		profile.category_weights = payload_categories
		profile.domain_weights = payload_domains

		db.add(profile)
		db.commit()
		db.refresh(profile)
		return profile

	def _load_recent_bookmarks(self, db: Session, user_id: Optional[str]) -> List[Bookmark]:
		from app.core.user_utils import normalize_user_id, GUEST_USER_ID
		# Normalize user_id so that None/empty and the string 'guest' are handled uniformly.
		normalized = normalize_user_id(user_id)

		query = db.query(Bookmark).options(
			joinedload(Bookmark.document).joinedload(Document.classifications),
		)
		# If normalized user is the guest sentinel, bookmarks are stored with the
		# literal 'guest' user_id in the DB. Use equality comparison for the
		# normalized value so both None (legacy) and 'guest' are covered.
		if normalized == GUEST_USER_ID:
			query = query.filter(Bookmark.user_id == GUEST_USER_ID)
		else:
			query = query.filter(Bookmark.user_id == normalized)
		query = query.order_by(Bookmark.created_at.desc()).limit(self.max_bookmarks)
		return list(query.all())

	def _compose_embedding_corpus(self, bookmarks: Sequence[Bookmark]) -> str:
		parts: List[str] = []
		remaining = max(self.embedding_char_limit, 0)
		for bookmark in bookmarks:
			doc = bookmark.document
			if not doc:
				continue
			fragments: List[str] = []
			if getattr(doc, "title", None):
				fragments.append(f"タイトル: {doc.title}")
			if getattr(doc, "short_summary", None):
				fragments.append(f"要約: {doc.short_summary}")
			elif getattr(doc, "content_text", None):
				fragments.append(f"本文: {doc.content_text[:500]}")
			elif getattr(doc, "content_md", None):
				fragments.append(f"本文: {doc.content_md[:500]}")
			if getattr(bookmark, "note", None):
				fragments.append(f"メモ: {bookmark.note}")
			block = "\n".join(fragment for fragment in fragments if fragment).strip()
			if not block:
				continue
			if remaining and len(block) > remaining:
				block = block[:remaining]
			parts.append(block)
			if remaining:
				remaining -= len(block)
			if remaining <= 0:
				break
		return "\n\n".join(parts).strip()

	def _compute_category_weights(self, bookmarks: Sequence[Bookmark]) -> Dict[str, float]:
		counter: Counter[str] = Counter()
		for bookmark in bookmarks:
			doc = bookmark.document
			if not doc:
				continue
			categories = getattr(doc, "classifications", []) or []
			for classification in categories:
				primary = getattr(classification, "primary_category", None)
				if primary:
					counter[str(primary)] += 1
					break
		total = sum(counter.values())
		if total == 0:
			return {}
		return {key: round(value / total, 4) for key, value in counter.items()}

	def _compute_domain_weights(self, bookmarks: Sequence[Bookmark]) -> Dict[str, float]:
		counter: Counter[str] = Counter()
		for bookmark in bookmarks:
			doc = bookmark.document
			if not doc:
				continue
			domain = getattr(doc, "domain", None)
			if domain:
				counter[str(domain)] += 1
		total = sum(counter.values())
		if total == 0:
			return {}
		return {key: round(value / total, 4) for key, value in counter.items()}

	def _get_profile(self, db: Session, user_id: Optional[str]) -> Optional[PreferenceProfile]:
		from app.core.user_utils import normalize_user_id
		# Normalize user_id so that we consistently query stored profiles using
		# the canonical representation (e.g. 'guest' for unidentified users).
		normalized = normalize_user_id(user_id)
		query = db.query(PreferenceProfile).filter(PreferenceProfile.user_id == normalized)
		return query.one_or_none()

	def _to_dto(self, profile: PreferenceProfile) -> PreferenceProfileDTO:
		embedding = tuple(_loads_float_list(profile.profile_embedding))
		category_weights = _loads_float_map(profile.category_weights)
		domain_weights = _loads_float_map(profile.domain_weights)
		status = _normalize_status(profile.status)

		return PreferenceProfileDTO(
			id=profile.id,
			user_id=profile.user_id,
			bookmark_count=profile.bookmark_count or 0,
			embedding=embedding,
			category_weights=category_weights,
			domain_weights=domain_weights,
			last_bookmark_id=profile.last_bookmark_id,
			status=status,
			created_at=profile.created_at or datetime.utcnow(),
			updated_at=profile.updated_at or datetime.utcnow(),
		)


__all__ = ["PreferenceProfileService"]
