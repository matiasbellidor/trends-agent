"""Hacker News vía la API de Algolia: portada del día + búsquedas por keyword."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..http import describe_error
from ..models import Item, Report
from ..textutil import clean_text
from ..timeutil import from_epoch

API = "https://hn.algolia.com/api/v1/search"


def _to_item(hit: dict) -> Item | None:
    title = hit.get("title") or hit.get("story_title")
    if not title:
        return None
    url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
    return Item(
        title=clean_text(title),
        url=url,
        source="hackernews",
        published=from_epoch(hit.get("created_at_i")),
        engagement=float(hit.get("points") or 0),
        summary=clean_text(hit.get("story_text"), 300),
    )


def fetch(cfg: dict, http, now: datetime, report: Report) -> list[Item]:
    found: dict[str, Item] = {}

    def collect(params: dict, label: str) -> None:
        try:
            data = http.get_json(API, params=params)
        except Exception as exc:  # una consulta caída no tira el resto
            report.error(f"hackernews {label}: {describe_error(exc)}")
            return
        for hit in data.get("hits", []):
            item = _to_item(hit)
            if item:
                found.setdefault(str(hit.get("objectID")), item)

    collect({"tags": "front_page", "hitsPerPage": cfg.get("limit", 60)}, "front_page")

    since = int((now - timedelta(hours=cfg.get("window_hours", 48))).timestamp())
    min_points = cfg.get("min_points", 20)
    for query in cfg.get("queries", []):
        collect(
            {
                "query": query,
                "tags": "story",
                "numericFilters": f"created_at_i>{since},points>{min_points}",
                "hitsPerPage": 15,
            },
            f"'{query}'",
        )
    return list(found.values())
