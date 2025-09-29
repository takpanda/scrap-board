"""Service helpers for recording personalized feedback events."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.database import Document, PreferenceFeedback, create_tables
from app.services.personalization_queue import schedule_profile_update

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PersonalizedFeedbackResult:
    """Result payload for feedback submissions."""

    created: bool
    state: str
    job_id: Optional[str] = None


class PersonalizedFeedbackService:
    """Store personalized ranking feedback and trigger recalculation jobs."""

    def __init__(self, db: Session):
        self._db = db

    def submit_low_relevance(
        self,
        *,
        document: Document,
        user_id: Optional[str],
        session_token: Optional[str],
        note: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PersonalizedFeedbackResult:
        """Persist a "low relevance" feedback record and enqueue a profile refresh.

        Duplicate submissions from the same user or the same browser session are
        ignored to keep the queue noise-free.
        """

        normalized_session = (session_token or "").strip() or None
        normalized_note = (note or "").strip() or None

        # Reject duplicates from the same authenticated user if a user id exists.
        if user_id:
            existing_for_user = (
                self._db.query(PreferenceFeedback)
                .filter(
                    PreferenceFeedback.document_id == document.id,
                    PreferenceFeedback.feedback_type == "low_relevance",
                    PreferenceFeedback.user_id == user_id,
                )
                .first()
            )
            if existing_for_user:
                return PersonalizedFeedbackResult(False, "duplicate_user")

        # Check duplicates for the same anonymous session token.
        if normalized_session:
            session_marker = normalized_session.replace("\"", "\\\"")
            existing_for_session = (
                self._db.query(PreferenceFeedback)
                .filter(
                    PreferenceFeedback.document_id == document.id,
                    PreferenceFeedback.feedback_type == "low_relevance",
                    PreferenceFeedback.metadata_payload != None,  # noqa: E711
                    PreferenceFeedback.metadata_payload.contains(
                        '"session_token": "' + session_marker + '"'
                    ),
                )
                .first()
            )
            if existing_for_session:
                return PersonalizedFeedbackResult(False, "duplicate_session")

        payload_dict: Dict[str, Any] = {}
        if normalized_session:
            payload_dict["session_token"] = normalized_session
        if normalized_note:
            payload_dict["note"] = normalized_note
        if metadata:
            payload_dict["metadata"] = metadata
        metadata_payload = (
            json.dumps(payload_dict, ensure_ascii=False) if payload_dict else None
        )

        feedback = PreferenceFeedback(
            user_id=user_id,
            document_id=document.id,
            feedback_type="low_relevance",
            metadata_payload=metadata_payload,
        )

        def _persist_feedback() -> Optional[PersonalizedFeedbackResult]:
            try:
                self._db.add(feedback)
                self._db.commit()
                self._db.refresh(feedback)
            except IntegrityError:
                self._db.rollback()
                logger.debug(
                    "personalized_feedback: duplicate feedback detected via integrity error",
                )
                return PersonalizedFeedbackResult(False, "duplicate_constraint")
            except OperationalError:
                self._db.rollback()
                try:
                    create_tables()
                except Exception:
                    logger.exception(
                        "personalized_feedback: create_tables failed after OperationalError",
                    )
                try:
                    self._db.add(feedback)
                    self._db.commit()
                    self._db.refresh(feedback)
                except Exception:
                    self._db.rollback()
                    logger.exception(
                        "personalized_feedback: failed to persist feedback after retry",
                    )
                    raise
            return None

        duplicate_result = _persist_feedback()
        if duplicate_result is not None:
            return duplicate_result

        job_id: Optional[str] = None
        try:
            job_id = schedule_profile_update(
                self._db,
                user_id=user_id,
                document_id=document.id,
                payload={
                    "reason": "feedback_low_relevance",
                    "feedback_id": feedback.id,
                },
            )
        except Exception:
            logger.exception(
                "personalized_feedback: failed to enqueue profile update job",
            )

        return PersonalizedFeedbackResult(True, "created", job_id)