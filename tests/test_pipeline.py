import json
from datetime import timedelta

import pytest

from fakes import NOW, FakeHttp, routes_ok, make_config
from trends_agent.cli import main
from trends_agent.pipeline import build_digest


def run(seen=None, now=NOW, youtube=False, config=None):
    return build_digest(config or make_config(), FakeHttp(routes_ok(youtube)), now, seen if seen is not None else {})


@pytest.fixture(autouse=True)
def no_youtube_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)


def test_end_to_end_filters_irrelevant_and_merges_crossposts():
    result = run()
    titles = [i.title for i in result.items]
    assert not any("sourdough" in t.lower() for t in titles)      # sin pilar: descartado
    assert any("gardening" in t.lower() for t in titles)          # feed topical: sobrevive por el piso de relevancia
    claude = [i for i in result.items if i.title.startswith("Claude Code tips")]
    assert len(claude) == 1                                        # HN + Reddit colapsan en uno
    assert len(claude[0].also_in) == 1


def test_scores_never_exceed_100_even_with_multi_source_bonus():
    assert all(0 <= i.score <= 100 for i in run().items)


def test_non_topical_feed_gets_no_floor():
    # sin topical, "gardening" no tiene pilar y se descarta
    config = make_config()
    config["sources"][-1]["feeds"][0]["topical"] = False
    titles = [i.title for i in run(config=config).items]
    assert not any("gardening" in t.lower() for t in titles)
    assert any("MCP" in t for t in titles)


def test_failed_source_is_reported_and_does_not_stop_the_run():
    result = run()
    assert any("reddit r/actuary" in e for e in result.report.errors)
    assert result.items, "las otras fuentes tienen que seguir"
    assert "## Fuentes con problemas" in result.markdown


def test_youtube_skipped_without_key_and_used_with_key(monkeypatch):
    result = run()
    assert any("youtube" in s and "YOUTUBE_API_KEY" in s for s in result.report.skipped)
    assert not any(i.source == "youtube" for i in result.items)

    monkeypatch.setenv("YOUTUBE_API_KEY", "dummy-key")
    result = run(youtube=True)
    assert any(i.source == "youtube" for i in result.items)
    assert not any("dummy-key" in e for e in result.report.errors)


def test_old_items_are_dropped():
    result = run(now=NOW + timedelta(days=10))
    assert result.items == []
    assert "Sin ítems nuevos hoy." in result.markdown


def test_second_day_excludes_already_shown_items():
    seen: dict[str, str] = {}
    first = run(seen=seen)
    assert first.items
    second = run(seen=seen, now=NOW + timedelta(days=1))
    shown = {i.url for i in first.items}
    assert not shown & {i.url for i in second.items}


def test_same_day_rerun_is_idempotent():
    seen: dict[str, str] = {}
    first = run(seen=seen)
    again = run(seen=seen)
    assert [i.url for i in first.items] == [i.url for i in again.items]


def test_digest_markdown_structure():
    md = run().markdown
    assert md.startswith("---\nfecha: 2026-10-21\ntipo: trends-digest")
    assert "## Actuarial y Data" in md
    assert "## Recolectado por fuente" in md
    assert "](https://" in md


def test_cli_writes_digest_and_seen_file(tmp_path, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    import yaml

    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump(make_config()), encoding="utf-8")
    out = tmp_path / "vault" / "07-trends"
    argv = [
        "run", "--config", str(cfg), "--out-dir", str(out),
        "--seen-file", str(out / ".seen.json"), "--now", "2026-10-21T12:00:00Z",
    ]
    assert main(argv, http=FakeHttp(routes_ok())) == 0
    digest = out / "2026-10-21.md"
    assert digest.exists() and "# Trends 2026-10-21" in digest.read_text(encoding="utf-8")
    assert json.loads((out / ".seen.json").read_text(encoding="utf-8"))


def test_cli_fails_when_every_source_fails(tmp_path):
    import requests
    import yaml

    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump(make_config()), encoding="utf-8")
    dead = FakeHttp([("", requests.ConnectionError("sin red"))])
    argv = ["run", "--config", str(cfg), "--out-dir", str(tmp_path / "o"), "--now", "2026-10-21T12:00:00Z"]
    assert main(argv, http=dead) == 2
    assert not (tmp_path / "o").exists()
