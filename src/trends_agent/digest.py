"""Selección y render del digest en Markdown (frontmatter compatible con Obsidian)."""
from __future__ import annotations

from collections import Counter, defaultdict

from .models import Item, Report

OTHER = "_otros"


def select(items: list[Item], max_items: int, per_pillar_cap: int) -> list[Item]:
    """Toma los mejores por score sin que un solo pilar se coma todo el digest."""
    counts: Counter[str] = Counter()
    chosen: list[Item] = []
    for it in items:
        key = it.top_pillar or OTHER
        if counts[key] >= per_pillar_cap:
            continue
        counts[key] += 1
        chosen.append(it)
        if len(chosen) >= max_items:
            break
    return chosen


def _link(title: str, url: str) -> str:
    safe_title = title.replace("[", "(").replace("]", ")")
    return f"[{safe_title}]({url.replace(')', '%29').replace(' ', '%20')})"


def _item_lines(it: Item, labels: dict[str, str], chars: int) -> list[str]:
    extra = "".join(f" +{s}" for s in it.also_in)
    lines = [f"- **{_link(it.title, it.url)}** — {it.source}{extra} · {it.score:.0f}"]
    detail = []
    if len(it.pillars) > 1:
        ranked = sorted(it.pillars, key=it.pillars.get, reverse=True)
        detail.append("Pilares: " + ", ".join(labels.get(p, p) for p in ranked))
    if it.summary:
        summary = it.summary if len(it.summary) <= chars else it.summary[: chars - 1].rstrip() + "…"
        detail.append(summary)
    if detail:
        lines.append("  " + " — ".join(detail))
    return lines


def render_digest(items: list[Item], date_str: str, report: Report, config: dict) -> str:
    pillars = config.get("pillars", {})
    labels = {k: v.get("label", k) for k, v in pillars.items()}
    order = sorted(pillars, key=lambda k: -float(pillars[k].get("weight", 1.0)))
    chars = int(config.get("digest", {}).get("summary_chars", 220))

    groups: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        groups[it.top_pillar or OTHER].append(it)

    out = [
        "---",
        f"fecha: {date_str}",
        "tipo: trends-digest",
        f"items: {len(items)}",
        f"fuentes_con_error: {len(report.errors)}",
        "---",
        "",
        f"# Trends {date_str}",
        "",
        "Generado por trends-agent. Pasalo por `/trends` para elegir ideas alineadas con los pilares.",
        "",
    ]
    if not items:
        out += ["Sin ítems nuevos hoy.", ""]
    for key in [*order, OTHER]:
        group = groups.get(key)
        if not group:
            continue
        out += [f"## {labels.get(key, 'Otros')}", ""]
        for it in group:
            out += _item_lines(it, labels, chars)
        out.append("")

    if report.counts:
        collected = " · ".join(f"{s} {n}" for s, n in sorted(report.counts.items()))
        out += ["## Recolectado por fuente", "", collected, ""]
    if report.errors:
        out += ["## Fuentes con problemas", "", *[f"- {e}" for e in report.errors], ""]
    if report.skipped:
        out += ["## Fuentes salteadas", "", *[f"- {s}" for s in report.skipped], ""]
    return "\n".join(out).rstrip() + "\n"
