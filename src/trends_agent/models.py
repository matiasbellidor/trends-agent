"""Modelos de datos compartidos por fuentes, scoring y digest."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class SkipSource(Exception):
    """La fuente no puede correr (por ejemplo, falta una API key). No es un error."""


@dataclass
class Item:
    title: str
    url: str
    source: str
    published: datetime | None = None
    # Puntos, estrellas, vistas o posición en el ranking. Solo es comparable
    # dentro de una misma fuente, por eso el scoring lo convierte a percentil.
    engagement: float = 0.0
    summary: str = ""
    # Fuente temática por definición (ej. un blog de IA): piso de relevancia.
    topical: bool = False
    pillars: dict[str, float] = field(default_factory=dict)  # pilar -> aporte
    relevance: float = 0.0
    score: float = 0.0
    also_in: list[str] = field(default_factory=list)

    @property
    def top_pillar(self) -> str | None:
        if not self.pillars:
            return None
        return max(self.pillars, key=self.pillars.get)


@dataclass
class Report:
    """Qué salió mal o se salteó en una corrida. Va al final del digest."""

    errors: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def skip(self, msg: str) -> None:
        self.skipped.append(msg)
