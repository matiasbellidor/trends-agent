"""arXiv: últimos papers por categoría (API Atom). Pide ~3 s entre consultas."""
from __future__ import annotations

import time
from datetime import datetime

import feedparser

from ..http import describe_error
from ..models import Item, Report
from ..textutil import clean_text
from ..timeutil import from_struct

API = "https://export.arxiv.org/api/query"


def fetch(cfg: dict, http, now: datetime, report: Report) -> list[Item]:
    pause = float(cfg.get("pause", 3))
    items: list[Item] = []
    for i, category in enumerate(cfg.get("categories", [])):
        if i and pause:
            time.sleep(pause)
        params = {
            "search_query": f"cat:{category}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": int(cfg.get("max_results", 25)),
        }
        try:
            text = http.get_text(API, params=params)
        except Exception as exc:
            report.error(f"arxiv {category}: {describe_error(exc)}")
            continue
        feed = feedparser.parse(text)
        if feed.bozo and not feed.entries:
            report.error(f"arxiv {category}: feed inválido")
            continue
        for entry in feed.entries:
            link, title = entry.get("link"), clean_text(entry.get("title"))
            if not link or not title:
                continue
            items.append(
                Item(
                    title=title,
                    url=link,
                    source=f"arxiv:{category}",
                    published=from_struct(entry.get("published_parsed")),
                    engagement=0.0,  # sin métrica: el score depende de relevancia y recencia
                    summary=clean_text(entry.get("summary"), 400),
                    topical=bool(cfg.get("topical", False)),
                )
            )
    return items
