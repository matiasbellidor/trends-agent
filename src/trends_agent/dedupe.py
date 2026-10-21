"""Deduplicación por URL normalizada y por similitud de título."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Item

_TRACKING = re.compile(r"^(utm_|mc_|ref$|ref_src$|fbclid$|gclid$|source$)", re.IGNORECASE)
_WORD = re.compile(r"\w+")


def normalize_url(url: str) -> str:
    p = urlsplit(url.strip())
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+$", "", p.path)
    if host.endswith("arxiv.org"):
        # /pdf/2401.01234v2.pdf y /abs/2401.01234v1 son el mismo paper
        path = re.sub(r"\.pdf$", "", path.replace("/pdf/", "/abs/"))
        path = re.sub(r"v\d+$", "", path)
    query = sorted(
        (k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not _TRACKING.match(k)
    )
    return urlunsplit(("https", host, path, urlencode(query), ""))


def _tokens(title: str) -> set[str]:
    return {t for t in _WORD.findall(title.lower()) if len(t) > 2}


def similar_titles(a: str, b: str, threshold: float = 0.8) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if len(ta) < 4 or len(tb) < 4:
        return False
    return len(ta & tb) / len(ta | tb) >= threshold


def merge_duplicates(items: list[Item]) -> list[Item]:
    """Colapsa duplicados. `items` debe venir ordenado por score descendente:
    se conserva el mejor y las otras fuentes quedan en `also_in`."""
    kept: list[Item] = []
    by_url: dict[str, Item] = {}
    for it in items:
        key = normalize_url(it.url)
        target = by_url.get(key)
        if target is None:
            target = next((k for k in kept if similar_titles(k.title, it.title)), None)
        if target is None:
            kept.append(it)
            by_url[key] = it
            continue
        if it.source != target.source and it.source not in target.also_in:
            target.also_in.append(it.source)
        by_url.setdefault(key, target)
    return kept
