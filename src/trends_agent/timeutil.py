"""Conversión de fechas de las distintas fuentes a datetime con zona UTC."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import struct_time


def from_struct(t: struct_time | None) -> datetime | None:
    if not t:
        return None
    return datetime(*t[:6], tzinfo=timezone.utc)


def from_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def from_epoch(n: float | int | None) -> datetime | None:
    if n is None:
        return None
    return datetime.fromtimestamp(float(n), tz=timezone.utc)


def local_date(now: datetime, offset_hours: float = -3) -> str:
    """Fecha local en formato YYYY-MM-DD. Argentina no tiene DST: offset fijo."""
    return now.astimezone(timezone(timedelta(hours=offset_hours))).strftime("%Y-%m-%d")
