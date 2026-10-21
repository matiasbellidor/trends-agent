"""Línea de comandos: python -m trends_agent run --config config.yaml --out-dir DIR"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .http import Http
from .pipeline import build_digest
from .state import load_seen, prune_seen, save_seen
from .timeutil import from_iso, local_date


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trends_agent")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="genera el digest del día")
    run.add_argument("--config", default="config.yaml")
    run.add_argument("--out-dir", default="out", help="carpeta donde se escribe AAAA-MM-DD.md")
    run.add_argument("--seen-file", help="JSON con ítems ya mostrados (evita repetir días)")
    run.add_argument("--now", help="fecha/hora ISO a usar en vez de la actual (para reproducir)")
    run.add_argument("--dry-run", action="store_true", help="imprime el digest sin escribir archivos")
    return parser


def main(argv: list[str] | None = None, http=None) -> int:
    args = _parser().parse_args(argv)
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    now = from_iso(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        print(f"--now inválido: {args.now}", file=sys.stderr)
        return 1

    today = local_date(now, config.get("timezone_offset_hours", -3))
    seen = prune_seen(load_seen(args.seen_file), today, int(config.get("seen_keep_days", 21)))

    result = build_digest(config, http or Http(), now, seen)

    # Si no se recolectó nada y hubo errores, no hay digest que valga: que el job falle.
    if not any(result.report.counts.values()) and result.report.errors:
        print("Todas las fuentes fallaron:", file=sys.stderr)
        for err in result.report.errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(result.markdown)
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.date}.md"
    path.write_text(result.markdown, encoding="utf-8")
    if args.seen_file:
        save_seen(args.seen_file, seen)
    print(f"Digest: {path} ({len(result.items)} ítems, {len(result.report.errors)} fuentes con error)")
    return 0
