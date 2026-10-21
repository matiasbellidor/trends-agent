"""Orquesta una corrida: recolectar -> filtrar -> puntuar -> deduplicar -> seleccionar."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from .dedupe import merge_duplicates
from .digest import render_digest, select
from .http import describe_error
from .models import Item, Report, SkipSource
from .scoring import apply_relevance, compile_pillars, score_items
from .sources import SOURCES
from .state import filter_unseen, mark_seen
from .timeutil import local_date


@dataclass
class Result:
    markdown: str
    items: list[Item]
    report: Report
    date: str


def collect(config: dict, http, now: datetime, report: Report) -> list[Item]:
    items: list[Item] = []
    for entry in config.get("sources", []):
        if not entry.get("enabled", True):
            continue
        kind = entry.get("type")
        fetch = SOURCES.get(kind)
        if fetch is None:
            report.error(f"{kind}: tipo de fuente desconocido")
            continue
        try:
            items.extend(fetch(entry, http, now, report))
        except SkipSource as exc:
            report.skip(f"{kind}: {exc}")
        except Exception as exc:  # una fuente rota no puede frenar el digest
            report.error(f"{kind}: {describe_error(exc)}")
    return items


def build_digest(config: dict, http, now: datetime, seen: dict[str, str]) -> Result:
    report = Report()
    today = local_date(now, config.get("timezone_offset_hours", -3))

    items = collect(config, http, now, report)
    report.counts = dict(Counter(i.source for i in items))

    max_age = timedelta(hours=float(config.get("max_age_hours", 96)))
    items = [i for i in items if i.published is None or now - i.published <= max_age]

    scoring_cfg = config.get("scoring", {})
    floor = float(scoring_cfg.get("topical_floor", 0.3))
    min_relevance = float(scoring_cfg.get("min_relevance", 0.12))
    compiled = compile_pillars(config.get("pillars", {}))

    relevant: list[Item] = []
    for it in items:
        apply_relevance(it, compiled)
        if it.relevance == 0 and it.topical:
            it.relevance = floor
        if it.relevance >= min_relevance:
            relevant.append(it)

    score_items(relevant, now, scoring_cfg)
    relevant.sort(key=lambda i: i.score, reverse=True)
    merged = merge_duplicates(relevant)

    # Aparecer en más de una fuente es una señal de tendencia real.
    bonus = float(scoring_cfg.get("multi_source_bonus", 5))
    cap = float(scoring_cfg.get("multi_source_bonus_cap", 10))
    for it in merged:
        if it.also_in:
            it.score = min(100.0, round(it.score + min(cap, bonus * len(it.also_in)), 1))
    merged.sort(key=lambda i: i.score, reverse=True)

    fresh = filter_unseen(merged, seen, today)
    digest_cfg = config.get("digest", {})
    chosen = select(
        fresh, int(digest_cfg.get("max_items", 30)), int(digest_cfg.get("per_pillar_cap", 10))
    )
    mark_seen(chosen, seen, today)

    return Result(render_digest(chosen, today, report, config), chosen, report, today)
