"""Registro de fuentes. Cada módulo expone fetch(cfg, http, now, report) -> list[Item]."""
from . import arxiv, github, hackernews, reddit, rss, youtube

SOURCES = {
    "hackernews": hackernews.fetch,
    "reddit": reddit.fetch,
    "github": github.fetch,
    "arxiv": arxiv.fetch,
    "youtube": youtube.fetch,
    "rss": rss.fetch,
}
