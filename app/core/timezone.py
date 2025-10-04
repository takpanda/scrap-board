from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

try:  # pragma: no cover - ZoneInfo is available on Python 3.9+
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for older Python
    ZoneInfo = None  # type: ignore

UTC = timezone.utc
JST = ZoneInfo("Asia/Tokyo") if ZoneInfo is not None else timezone(timedelta(hours=9))


def ensure_aware(dt: Optional[datetime], default_tz: timezone = UTC) -> Optional[datetime]:
    """Return a timezone-aware datetime.

    Naive datetimes are assumed to be expressed in ``default_tz`` (UTC by default).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    return dt


def to_jst(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert ``dt`` to Japan Standard Time."""
    aware = ensure_aware(dt)
    if aware is None:
        return None
    try:
        return aware.astimezone(JST)
    except Exception:
        # As a fallback, treat the datetime as naive and append JST tzinfo.
        return aware.replace(tzinfo=JST)


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert ``dt`` to UTC."""
    aware = ensure_aware(dt)
    if aware is None:
        return None
    return aware.astimezone(UTC)


def to_utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Return a naive UTC datetime suitable for comparisons in UTC-based storage."""
    converted = to_utc(dt)
    if converted is None:
        return None
    return converted.replace(tzinfo=None)


def jst_isoformat(dt: Optional[datetime]) -> Optional[str]:
    """Return the ISO 8601 string in JST (``None`` if input is ``None``)."""
    converted = to_jst(dt)
    if converted is None:
        return None
    return converted.isoformat()


def format_jst(dt: Optional[datetime], fmt: str) -> str:
    """Format ``dt`` in JST using the provided format string."""
    converted = to_jst(dt)
    if converted is None:
        return ""
    try:
        return converted.strftime(fmt)
    except Exception:
        return converted.isoformat()
