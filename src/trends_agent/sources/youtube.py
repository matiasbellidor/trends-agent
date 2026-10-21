"""YouTube Data API v3 (opcional: requiere YOUTUBE_API_KEY).

Costo de cuota: search.list = 100 unidades + videos.list = 1 por consulta.
Con 5 consultas diarias son ~505 de las 10.000 unidades gratis por día.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from ..http import describe_error
from ..models import Item, Report, SkipSource
from ..textutil import clean_text
from ..timeutil import from_iso

SEARCH = "https://www.googleapis.com/youtube/v3/search"
VIDEOS = "https://www.googleapis.com/youtube/v3/videos"


def fetch(cfg: dict, http, now: datetime, report: Report) -> list[Item]:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise SkipSource("falta YOUTUBE_API_KEY")

    after = (now - timedelta(days=int(cfg.get("window_days", 7)))).astimezone(timezone.utc)
    published_after = after.strftime("%Y-%m-%dT%H:%M:%SZ")
    found: dict[str, Item] = {}

    for query in cfg.get("queries", []):
        search_params = {
            "key": key,
            "part": "snippet",
            "type": "video",
            "order": "viewCount",
            "q": query,
            "publishedAfter": published_after,
            "regionCode": cfg.get("region", "AR"),
            "relevanceLanguage": cfg.get("language", "es"),
            "maxResults": int(cfg.get("per_query", 10)),
        }
        try:
            ids = [
                hit["id"]["videoId"]
                for hit in http.get_json(SEARCH, params=search_params).get("items", [])
                if hit.get("id", {}).get("videoId")
            ]
            if not ids:
                continue
            stats = http.get_json(
                VIDEOS, params={"key": key, "part": "snippet,statistics", "id": ",".join(ids)}
            )
        except Exception as exc:  # el mensaje no incluye la URL, que lleva la key
            report.error(f"youtube '{query}': {describe_error(exc)}")
            continue
        for video in stats.get("items", []):
            vid, snippet = video["id"], video.get("snippet", {})
            found.setdefault(
                vid,
                Item(
                    title=clean_text(snippet.get("title")),
                    url=f"https://www.youtube.com/watch?v={vid}",
                    source="youtube",
                    published=from_iso(snippet.get("publishedAt")),
                    engagement=float(video.get("statistics", {}).get("viewCount") or 0),
                    summary=clean_text(snippet.get("description"), 300),
                ),
            )
    return list(found.values())
