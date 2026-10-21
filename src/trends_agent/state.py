"""Memoria de ítems ya mostrados, para que el digest no repita lo de ayer."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .dedupe import normalize_url
from .models import Item


def load_seen(path: str | Path | None) -> dict[str, str]:
    if not path or not Path(path).exists():
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def prune_seen(seen: dict[str, str], today: str, keep_days: int) -> dict[str, str]:
    limit = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    return {k: d for k, d in seen.items() if d >= limit}


def filter_unseen(items: list[Item], seen: dict[str, str], today: str) -> list[Item]:
    """Descarta lo mostrado en días anteriores. Lo mostrado hoy se conserva,
    así volver a correr el mismo día regenera el mismo digest."""
    return [i for i in items if seen.get(normalize_url(i.url), today) == today]


def mark_seen(items: list[Item], seen: dict[str, str], today: str) -> None:
    for it in items:
        seen.setdefault(normalize_url(it.url), today)


def save_seen(path: str | Path, seen: dict[str, str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(dict(sorted(seen.items())), indent=0, ensure_ascii=False), encoding="utf-8"
    )
