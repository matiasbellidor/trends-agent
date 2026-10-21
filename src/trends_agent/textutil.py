"""Limpieza de texto: HTML de feeds a texto plano corto."""
from __future__ import annotations

import html
import re

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def clean_text(s: str | None, limit: int | None = None) -> str:
    # Primero se sacan los tags y después se decodifican las entidades,
    # para que un "&lt;" escrito como texto no se interprete como tag.
    text = html.unescape(_TAG.sub(" ", s or ""))
    text = _WS.sub(" ", text).strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text
