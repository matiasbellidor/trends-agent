"""Feeds RSS/Atom genéricos (blogs y newsletters)."""
from __future__ import annotations

from datetime import datetime

import feedparser

from ..http import describe_error
from ..models import Item, Report
from ..textutil import clean_text
from ..timeutil import from_struct


def fetch(cfg: dict, http, now: datetime, report: Report) -> list[Item]:
    items: list[Item] = []
    per_feed = int(cfg.get("per_feed", 10))
    for feed_cfg in cfg.get("feeds", []):
        name, url = feed_cfg.get("name", feed_cfg["url"]), feed_cfg["url"]
        try:
            text = http.get_text(url)
        except Exception as exc:
            report.error(f"rss {name}: {describe_error(exc)}")
            continue
        feed = feedparser.parse(text)
        if feed.bozo and not feed.entries:
            report.error(f"rss {name}: feed inválido")
            continue
        for entry in feed.entries[:per_feed]:
            link, title = entry.get("link"), clean_text(entry.get("title"))
            if not link or not title:
                continue
            items.append(
                Item(
                    title=title,
                    url=link,
                    source=f"rss:{name}",
                    published=from_struct(entry.get("published_parsed") or entry.get("updated_parsed")),
                    engagement=0.0,
                    summary=clean_text(entry.get("summary"), 300),
                    topical=bool(feed_cfg.get("topical", False)),
                )
            )
    return items
