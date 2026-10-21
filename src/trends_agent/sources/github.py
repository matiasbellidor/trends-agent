"""GitHub: repos nuevos con más estrellas por topic (API de búsqueda)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from ..http import describe_error
from ..models import Item, Report
from ..textutil import clean_text
from ..timeutil import from_iso

API = "https://api.github.com/search/repositories"


def fetch(cfg: dict, http, now: datetime, report: Report) -> list[Item]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:  # sin token el límite de búsqueda es 10 req/min; con token, 30
        headers["Authorization"] = f"Bearer {token}"

    since = (now - timedelta(days=int(cfg.get("window_days", 7)))).strftime("%Y-%m-%d")
    found: dict[str, Item] = {}

    for topic in cfg.get("topics", []):
        name, min_stars = (
            (topic["name"], topic.get("min_stars", 20)) if isinstance(topic, dict) else (topic, 20)
        )
        params = {
            "q": f"topic:{name} created:>{since} stars:>={min_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": int(cfg.get("per_topic", 10)),
        }
        try:
            data = http.get_json(API, params=params, headers=headers)
        except Exception as exc:
            report.error(f"github topic:{name}: {describe_error(exc)}")
            continue
        for repo in data.get("items", []):
            full_name = repo.get("full_name")
            if not full_name:
                continue
            description = clean_text(repo.get("description"), 200)
            topics = ", ".join(repo.get("topics", [])[:6])
            found.setdefault(
                full_name,
                Item(
                    title=f"{full_name}: {description}" if description else full_name,
                    url=repo.get("html_url") or f"https://github.com/{full_name}",
                    source="github",
                    published=from_iso(repo.get("created_at")),
                    engagement=float(repo.get("stargazers_count") or 0),
                    summary=" ".join(filter(None, [description, topics])),
                ),
            )
    return list(found.values())
