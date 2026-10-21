"""Reddit vía feeds RSS públicos (sin API key). El orden del feed es el ranking."""
from __future__ import annotations

from datetime import datetime

import feedparser

from ..http import describe_error
from ..models import Item, Report
from ..textutil import clean_text
from ..timeutil import from_struct

DEFAULT_UA = (
    "trends-agent/0.1 (digest personal; "
    "https://github.com/matiasbellidor/trends-agent)"
)


def fetch(cfg: dict, http, now: datetime, report: Report) -> list[Item]:
    period = cfg.get("period", "day")
    limit = int(cfg.get("limit", 15))
    headers = {"User-Agent": cfg.get("user_agent", DEFAULT_UA)}
    items: list[Item] = []

    for sub in cfg.get("subreddits", []):
        url = f"https://www.reddit.com/r/{sub}/top/.rss"
        try:
            text = http.get_text(url, params={"t": period}, headers=headers)
        except Exception as exc:
            report.error(f"reddit r/{sub}: {describe_error(exc)}")
            continue
        feed = feedparser.parse(text)
        if feed.bozo and not feed.entries:
            report.error(f"reddit r/{sub}: feed inválido")
            continue
        entries = feed.entries[:limit]
        for idx, entry in enumerate(entries):
            link = entry.get("link")
            title = clean_text(entry.get("title"))
            if not link or not title:
                continue
            items.append(
                Item(
                    title=title,
                    url=link,
                    source=f"reddit:{sub}",
                    published=from_struct(entry.get("published_parsed") or entry.get("updated_parsed")),
                    # El RSS no trae score: la posición en el top es la señal.
                    engagement=float(len(entries) - idx),
                    summary=clean_text(entry.get("summary"), 300),
                )
            )
    return items
