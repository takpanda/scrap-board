from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Literal

PreferenceProfileStatus = Literal["active", "cold_start", "error"]


def _clip_unit(value: float) -> float:
	"""Clamp a numeric value into the inclusive range [0, 1]."""

	if value is None:
		return 0.0
	return max(0.0, min(1.0, float(value)))


def _coerce_vector(values: Optional[Sequence[float]]) -> Tuple[float, ...]:
	"""Coerce any sequence of numeric values into a tuple[float, ...]."""

	if values is None:
		return ()
	return tuple(float(v) for v in values)


def _coerce_float_map(data: Optional[Mapping[str, float]]) -> Dict[str, float]:
	if not data:
		return {}
	return {str(key): float(value) for key, value in data.items()}


def _coerce_datetime(value: Any) -> datetime:
	if isinstance(value, datetime):
		return value
	if isinstance(value, str):
		try:
			return datetime.fromisoformat(value)
		except ValueError:
			pass
	return datetime.utcnow()


@dataclass(frozen=True)
class ExplanationBreakdown:
	"""Represents the contribution of each scoring component."""

	similarity: float = 0.0
	category: float = 0.0
	domain: float = 0.0
	freshness: float = 0.0
	note: Optional[str] = None

	def __post_init__(self) -> None:
		object.__setattr__(self, "similarity", _clip_unit(self.similarity))
		object.__setattr__(self, "category", _clip_unit(self.category))
		object.__setattr__(self, "domain", _clip_unit(self.domain))
		object.__setattr__(self, "freshness", _clip_unit(self.freshness))

	def clamped(self) -> ExplanationBreakdown:
		"""Return a new instance that is explicitly clamped to [0, 1]."""

		return ExplanationBreakdown(
			similarity=_clip_unit(self.similarity),
			category=_clip_unit(self.category),
			domain=_clip_unit(self.domain),
			freshness=_clip_unit(self.freshness),
			note=self.note,
		)

	def to_dict(self) -> Dict[str, Any]:
		data: Dict[str, Any] = {
			"similarity": self.similarity,
			"category": self.category,
			"domain": self.domain,
			"freshness": self.freshness,
		}
		if self.note is not None:
			data["note"] = self.note
		return data

	@classmethod
	def from_dict(cls, payload: Mapping[str, Any]) -> ExplanationBreakdown:
		return cls(
			similarity=float(payload.get("similarity", 0.0)),
			category=float(payload.get("category", 0.0)),
			domain=float(payload.get("domain", 0.0)),
			freshness=float(payload.get("freshness", 0.0)),
			note=payload.get("note"),
		)

	@property
	def total(self) -> float:
		return self.similarity + self.category + self.domain + self.freshness


@dataclass(frozen=True)
class PreferenceProfileDTO:
	"""Immutable representation of the preference profile stored in the DB."""

	id: str
	user_id: Optional[str]
	bookmark_count: int
	embedding: Tuple[float, ...] = field(default_factory=tuple)
	category_weights: Dict[str, float] = field(default_factory=dict)
	domain_weights: Dict[str, float] = field(default_factory=dict)
	last_bookmark_id: Optional[str] = None
	status: PreferenceProfileStatus = "active"
	created_at: datetime = field(default_factory=datetime.utcnow)
	updated_at: datetime = field(default_factory=datetime.utcnow)

	def __post_init__(self) -> None:
		object.__setattr__(self, "embedding", _coerce_vector(self.embedding))
		object.__setattr__(self, "category_weights", _coerce_float_map(self.category_weights))
		object.__setattr__(self, "domain_weights", _coerce_float_map(self.domain_weights))
		object.__setattr__(self, "created_at", _coerce_datetime(self.created_at))
		object.__setattr__(self, "updated_at", _coerce_datetime(self.updated_at))

	@property
	def is_cold_start(self) -> bool:
		return self.status == "cold_start" or self.bookmark_count < 3

	def with_status(self, status: PreferenceProfileStatus) -> PreferenceProfileDTO:
		return replace(self, status=status)

	def with_updated_timestamp(self, updated_at: datetime) -> PreferenceProfileDTO:
		return replace(self, updated_at=updated_at)

	def to_payload(self) -> Dict[str, Any]:
		return {
			"id": self.id,
			"user_id": self.user_id,
			"bookmark_count": self.bookmark_count,
			"embedding": list(self.embedding),
			"category_weights": dict(self.category_weights),
			"domain_weights": dict(self.domain_weights),
			"last_bookmark_id": self.last_bookmark_id,
			"status": self.status,
			"created_at": self.created_at,
			"updated_at": self.updated_at,
		}

	@classmethod
	def from_payload(cls, payload: Mapping[str, Any]) -> PreferenceProfileDTO:
		return cls(
			id=str(payload["id"]),
			user_id=payload.get("user_id"),
			bookmark_count=int(payload.get("bookmark_count", 0)),
			embedding=_coerce_vector(payload.get("embedding", ())),
			category_weights=_coerce_float_map(payload.get("category_weights")),
			domain_weights=_coerce_float_map(payload.get("domain_weights")),
			last_bookmark_id=payload.get("last_bookmark_id"),
			status=payload.get("status", "active"),
			created_at=_coerce_datetime(payload.get("created_at")),
			updated_at=_coerce_datetime(payload.get("updated_at")),
		)


@dataclass(frozen=True)
class PersonalizedScoreDTO:
	"""Aggregated personalization score for a document."""

	id: str
	document_id: str
	score: float
	rank: int
	components: ExplanationBreakdown
	explanation: str
	computed_at: datetime
	user_id: Optional[str] = None
	cold_start: bool = False

	def __post_init__(self) -> None:
		object.__setattr__(self, "score", _clip_unit(self.score))
		object.__setattr__(self, "rank", int(self.rank))

		components = self.components
		if isinstance(components, Mapping):
			components = ExplanationBreakdown.from_dict(components)
		object.__setattr__(self, "components", components.clamped())
		object.__setattr__(self, "computed_at", _coerce_datetime(self.computed_at))

	def with_rank(self, rank: int) -> PersonalizedScoreDTO:
		return replace(self, rank=int(rank))

	def clamp_score(self) -> PersonalizedScoreDTO:
		return replace(self, score=_clip_unit(self.score), components=self.components.clamped())

	def to_payload(self) -> Dict[str, Any]:
		return {
			"id": self.id,
			"document_id": self.document_id,
			"user_id": self.user_id,
			"score": self.score,
			"rank": self.rank,
			"components": self.components.to_dict(),
			"explanation": self.explanation,
			"computed_at": self.computed_at,
			"cold_start": self.cold_start,
		}

	@classmethod
	def from_payload(cls, payload: Mapping[str, Any]) -> PersonalizedScoreDTO:
		components = payload.get("components", {})
		if isinstance(components, Mapping):
			components_obj = ExplanationBreakdown.from_dict(components)
		else:
			components_obj = components

		return cls(
			id=str(payload["id"]),
			document_id=str(payload["document_id"]),
			user_id=payload.get("user_id"),
			score=float(payload.get("score", 0.0)),
			rank=int(payload.get("rank", 0)),
			components=components_obj,
			explanation=str(payload.get("explanation", "")),
			computed_at=_coerce_datetime(payload.get("computed_at")),
			cold_start=bool(payload.get("cold_start", False)),
		)


__all__ = [
	"PreferenceProfileDTO",
	"PersonalizedScoreDTO",
	"ExplanationBreakdown",
	"PreferenceProfileStatus",
]
