"""Relevancia por pilares + engagement relativo + recencia -> score 0-100."""
from __future__ import annotations

import re
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime

from .models import Item

Compiled = dict[str, tuple[float, list[re.Pattern]]]


def compile_pillars(pillars_cfg: dict) -> Compiled:
    compiled: Compiled = {}
    for name, p in pillars_cfg.items():
        patterns = [
            re.compile(rf"(?<!\w){re.escape(str(kw))}(?!\w)", re.IGNORECASE)
            for kw in p.get("keywords", [])
        ]
        compiled[name] = (float(p.get("weight", 1.0)), patterns)
    return compiled


def apply_relevance(item: Item, compiled: Compiled) -> None:
    """Cada keyword suma 2 si está en el título y 1 si solo está en el resumen.
    El aporte de un pilar es peso * min(hits, 4) / 4."""
    body = item.summary[:600]
    contrib: dict[str, float] = {}
    for name, (weight, patterns) in compiled.items():
        hits = 0
        for pat in patterns:
            if pat.search(item.title):
                hits += 2
            elif pat.search(body):
                hits += 1
        if hits:
            contrib[name] = weight * min(hits, 4) / 4
    item.pillars = contrib
    item.relevance = min(1.0, sum(contrib.values()))


def percentile_ranks(values: list[float]) -> list[float]:
    """Percentil de cada valor en [0, 1]; empates reciben el rango promedio.
    Si todos los valores son iguales (ej. RSS sin métricas) devuelve 0.5."""
    n = len(values)
    if n == 0:
        return []
    if len(set(values)) == 1:
        return [0.5] * n
    ordered = sorted(values)
    return [
        (bisect_left(ordered, v) + bisect_right(ordered, v) - 1) / 2 / (n - 1) for v in values
    ]


def recency(item: Item, now: datetime, half_life_hours: float) -> float:
    if item.published is None:
        return 0.5
    age_h = max(0.0, (now - item.published).total_seconds() / 3600)
    return 0.5 ** (age_h / half_life_hours)


def score_items(items: list[Item], now: datetime, cfg: dict) -> None:
    w = cfg.get("weights", {})
    w_rel = float(w.get("relevance", 0.5))
    w_eng = float(w.get("engagement", 0.3))
    w_rec = float(w.get("recency", 0.2))
    half_life = float(cfg.get("half_life_hours", 36))

    groups: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        groups[it.source].append(it)
    for group in groups.values():
        ranks = percentile_ranks([i.engagement for i in group])
        for it, rank in zip(group, ranks):
            it.score = round(
                100 * (w_rel * it.relevance + w_eng * rank + w_rec * recency(it, now, half_life)),
                1,
            )
