from datetime import timedelta

import yaml
from pathlib import Path

from fakes import NOW
from trends_agent.dedupe import merge_duplicates, normalize_url, similar_titles
from trends_agent.models import Item
from trends_agent.scoring import apply_relevance, compile_pillars, percentile_ranks, recency
from trends_agent.sources import SOURCES
from trends_agent.state import filter_unseen, load_seen, mark_seen, prune_seen, save_seen
from trends_agent.textutil import clean_text


def test_normalize_url_strips_tracking_www_fragment_and_slash():
    a = normalize_url("http://www.Example.com/post/?utm_source=x&b=2&a=1#frag")
    b = normalize_url("https://example.com/post?a=1&b=2")
    assert a == b


def test_normalize_url_keeps_youtube_video_id():
    assert "v=abc" in normalize_url("https://www.youtube.com/watch?v=abc&utm_medium=x")


def test_normalize_url_arxiv_versions_and_pdf():
    assert (
        normalize_url("http://arxiv.org/abs/2610.01234v2")
        == normalize_url("https://arxiv.org/pdf/2610.01234v1.pdf")
    )


def test_similar_titles_needs_enough_tokens():
    assert similar_titles("Claude Code tips for data analysts", "claude code tips for data analysts!")
    assert not similar_titles("Claude Code", "Claude Code")  # muy corto para decidir
    assert not similar_titles("Claude Code tips for analysts", "Sourdough baking at home tonight")


def test_merge_duplicates_keeps_best_and_records_other_sources():
    best = Item("Claude Code tips for data analysts", "https://a.com/x", "hackernews", score=80)
    dup = Item("Claude Code tips for data analysts", "https://reddit.com/r/y", "reddit:datascience", score=60)
    same_source = Item("Otro", "https://a.com/x/", "hackernews", score=10)
    merged = merge_duplicates([best, dup, same_source])
    assert merged == [best]
    assert best.also_in == ["reddit:datascience"]


def test_percentile_ranks_ties_and_flat():
    assert percentile_ranks([1, 2, 3]) == [0.0, 0.5, 1.0]
    assert percentile_ranks([1, 1, 3]) == [0.25, 0.25, 1.0]
    assert percentile_ranks([5, 5]) == [0.5, 0.5]
    assert percentile_ranks([]) == []


def test_relevance_title_counts_double_and_word_boundaries():
    cfg = {"p": {"weight": 1.0, "keywords": ["sql", "pandas", "dashboard", "mcp"]}}
    compiled = compile_pillars(cfg)
    in_title = Item("SQL and pandas tricks", "u", "s")
    in_body = Item("Tricks", "u", "s", summary="about sql and pandas")
    substring_only = Item("MySQL and NoSQL", "u", "s")
    for it in (in_title, in_body, substring_only):
        apply_relevance(it, compiled)
    assert in_title.relevance == 1.0          # 2 keywords * 2 puntos = 4 hits
    assert in_body.relevance == 0.5           # 2 hits
    assert substring_only.relevance == 0.0    # "sql" dentro de MySQL no cuenta


def test_relevance_caps_at_one_across_pillars():
    cfg = {
        "a": {"weight": 1.0, "keywords": ["sql", "pandas"]},
        "b": {"weight": 1.0, "keywords": ["claude", "llm"]},
    }
    it = Item("SQL pandas claude llm", "u", "s")
    apply_relevance(it, compile_pillars(cfg))
    assert it.relevance == 1.0
    assert set(it.pillars) == {"a", "b"}


def test_recency_halves_at_half_life():
    fresh = Item("t", "u", "s", published=NOW)
    old = Item("t", "u", "s", published=NOW - timedelta(hours=36))
    unknown = Item("t", "u", "s")
    assert recency(fresh, NOW, 36) == 1.0
    assert abs(recency(old, NOW, 36) - 0.5) < 1e-9
    assert recency(unknown, NOW, 36) == 0.5


def test_seen_semantics_same_day_rerun_keeps_items(tmp_path):
    item = Item("t", "https://a.com/x", "s")
    seen: dict[str, str] = {}
    assert filter_unseen([item], seen, "2026-10-21") == [item]
    mark_seen([item], seen, "2026-10-21")
    assert filter_unseen([item], seen, "2026-10-21") == [item]  # mismo día: se conserva
    assert filter_unseen([item], seen, "2026-10-22") == []      # día siguiente: se descarta

    path = tmp_path / "state" / ".seen.json"
    save_seen(path, seen)
    assert load_seen(path) == seen
    assert prune_seen(seen, "2026-12-31", 21) == {}


def test_load_seen_tolerates_corrupt_file(tmp_path):
    bad = tmp_path / "seen.json"
    bad.write_text("{no es json", encoding="utf-8")
    assert load_seen(bad) == {}


def test_clean_text_strips_html_then_decodes_entities():
    assert clean_text("<p>Hola &amp; <b>chau</b></p>") == "Hola & chau"
    assert clean_text("a &lt;b&gt; c") == "a <b> c"
    assert clean_text("x" * 50, limit=10) == "x" * 9 + "…"


def test_shipped_config_is_valid():
    config = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8"))
    assert config["pillars"], "faltan pilares"
    for name, pillar in config["pillars"].items():
        assert pillar["keywords"], f"{name} sin keywords"
        assert float(pillar["weight"]) > 0
    for source in config["sources"]:
        assert source["type"] in SOURCES, f"fuente desconocida: {source['type']}"
    w = config["scoring"]["weights"]
    assert abs(sum(w.values()) - 1.0) < 1e-9
