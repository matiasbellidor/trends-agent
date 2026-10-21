"""HTTP simulado y respuestas de ejemplo para probar todo sin red."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)


def epoch(hours_ago: float) -> int:
    return int((NOW - timedelta(hours=hours_ago)).timestamp())


def iso(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeHttp:
    """routes: lista de (fragmento_de_url, respuesta | excepción). Gana la primera que matchea."""

    def __init__(self, routes):
        self.routes = routes
        self.calls: list[str] = []

    def _lookup(self, url, params):
        key = url + ("?" + urlencode(params) if params else "")
        self.calls.append(key)
        for fragment, payload in self.routes:
            if fragment in key:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise requests.ConnectionError(f"sin ruta simulada para {key}")

    def get_json(self, url, params=None, headers=None):
        return self._lookup(url, params)

    def get_text(self, url, params=None, headers=None):
        return self._lookup(url, params)


HN_FRONT = {
    "hits": [
        {
            "objectID": "1001",
            "title": "Claude Code tips for data analysts",
            "url": "https://example.com/claude-tips?utm_source=hn",
            "points": 420,
            "created_at_i": epoch(5),
        },
        {
            "objectID": "1002",
            "title": "Show HN: A SQL dashboard in the browser",
            "url": "https://example.org/sql-dash",
            "points": 150,
            "created_at_i": epoch(10),
        },
        {
            "objectID": "1003",
            "title": "Ask HN: Favorite sourdough recipes",
            "url": None,
            "points": 300,
            "created_at_i": epoch(3),
        },
    ]
}

HN_QUERY_ACTUARIAL = {
    "hits": [
        {
            "objectID": "1004",
            "title": "Actuarial reserving with Python and polars",
            "url": "https://example.net/reserving",
            "points": 40,
            "created_at_i": epoch(20),
        },
        # duplicado de la portada: tiene que colapsar por objectID
        {
            "objectID": "1002",
            "title": "Show HN: A SQL dashboard in the browser",
            "url": "https://example.org/sql-dash",
            "points": 150,
            "created_at_i": epoch(10),
        },
    ]
}

REDDIT_DATASCIENCE = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>top</title>
  <entry>
    <title>Claude Code tips for data analysts</title>
    <link href="https://www.reddit.com/r/datascience/comments/abc/claude_code_tips/"/>
    <updated>{iso(6)}</updated>
    <content type="html">&lt;p&gt;Using Claude Code with pandas notebooks&lt;/p&gt;</content>
  </entry>
  <entry>
    <title>Weekly entering and transitioning thread</title>
    <link href="https://www.reddit.com/r/datascience/comments/def/weekly/"/>
    <updated>{iso(8)}</updated>
    <content type="html">&lt;p&gt;Ask your questions here&lt;/p&gt;</content>
  </entry>
</feed>"""

ARXIV = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>arXiv Query</title>
  <entry>
    <id>http://arxiv.org/abs/2610.01234v1</id>
    <title>Bayesian loss reserving
      with stochastic claims</title>
    <summary>We study reserving for insurance portfolios using survival analysis.</summary>
    <published>{iso(30)}</published>
    <link href="http://arxiv.org/abs/2610.01234v1" rel="alternate" type="text/html"/>
  </entry>
</feed>"""

GITHUB = {
    "items": [
        {
            "full_name": "someone/obsidian-claude",
            "html_url": "https://github.com/someone/obsidian-claude",
            "description": "Obsidian vault templates for Claude Code",
            "stargazers_count": 85,
            "created_at": iso(48),
            "topics": ["obsidian", "claude-code"],
        }
    ]
}

RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>blog</title>
  <item>
    <title>Notes on building agents with MCP</title>
    <link>https://blog.example.com/mcp-agents</link>
    <pubDate>Wed, 21 Oct 2026 06:00:00 GMT</pubDate>
    <description>&lt;p&gt;A practical look at an LLM agent.&lt;/p&gt;</description>
  </item>
  <item>
    <title>My thoughts on gardening</title>
    <link href="https://blog.example.com/garden"/>
    <link>https://blog.example.com/garden</link>
    <pubDate>Wed, 21 Oct 2026 07:00:00 GMT</pubDate>
    <description>Tomatoes.</description>
  </item>
</channel></rss>"""

YT_SEARCH = {"items": [{"id": {"videoId": "vid1"}}]}
YT_VIDEOS = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "Cómo usar Claude Code para análisis de datos",
                "publishedAt": iso(24),
                "description": "Tutorial con python y pandas",
            },
            "statistics": {"viewCount": "5400"},
        }
    ]
}


def make_config() -> dict:
    return {
        "timezone_offset_hours": -3,
        "max_age_hours": 96,
        "seen_keep_days": 21,
        "scoring": {
            "weights": {"relevance": 0.5, "engagement": 0.3, "recency": 0.2},
            "half_life_hours": 36,
            "min_relevance": 0.12,
            "topical_floor": 0.3,
            "multi_source_bonus": 5,
            "multi_source_bonus_cap": 10,
        },
        "digest": {"max_items": 30, "per_pillar_cap": 10, "summary_chars": 220},
        "pillars": {
            "actuarial_data": {
                "label": "Actuarial y Data",
                "weight": 1.0,
                "keywords": ["actuarial", "reserving", "sql", "pandas", "data analysis",
                             "data analysts", "survival analysis", "dashboard", "stochastic"],
            },
            "ia_productividad": {
                "label": "IA aplicada a productividad",
                "weight": 0.9,
                "keywords": ["claude", "claude code", "llm", "mcp", "obsidian", "agent"],
            },
            "proyectos_tecnicos": {
                "label": "Proyectos técnicos",
                "weight": 0.6,
                "keywords": ["python", "polars"],
            },
        },
        "sources": [
            {"type": "hackernews", "limit": 60, "min_points": 25, "queries": ["actuarial"]},
            {"type": "reddit", "subreddits": ["datascience", "actuary"], "limit": 15},
            {"type": "github", "topics": [{"name": "obsidian", "min_stars": 30}]},
            {"type": "arxiv", "categories": ["stat.AP"], "pause": 0},
            {"type": "youtube", "queries": ["claude code"]},
            {"type": "rss", "feeds": [{"name": "blog", "url": "https://blog.example.com/feed", "topical": True}]},
        ],
    }


def routes_ok(youtube: bool = False):
    routes = [
        ("hn.algolia.com", None),  # se reemplaza abajo; mantiene el orden legible
    ]
    routes = [
        ("query=actuarial", HN_QUERY_ACTUARIAL),
        ("tags=front_page", HN_FRONT),
        ("r/datascience", REDDIT_DATASCIENCE),
        ("r/actuary", requests.ConnectionError("boom")),
        ("api.github.com/search", GITHUB),
        ("export.arxiv.org", ARXIV),
        ("blog.example.com/feed", RSS),
    ]
    if youtube:
        routes += [("youtube/v3/search", YT_SEARCH), ("youtube/v3/videos", YT_VIDEOS)]
    return routes
