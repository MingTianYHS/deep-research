import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.budget import BudgetExceeded, apply_delta, report
from lib.evidence import canonical_url, ingest_worker_result
from lib.tool_registry import load_registry, resolve, validate_registry


def test_budget_rejects_overspend():
    state = {"usage": {"queries": 7}}
    profile = {"max_queries": 8, "max_pages": 10, "max_evidence_cards": 10, "estimated_input_tokens": 100, "estimated_output_tokens": 100}
    try:
        apply_delta(state, profile, {"queries": 2})
        assert False, "expected BudgetExceeded"
    except BudgetExceeded:
        pass
    assert state["usage"]["queries"] == 7


def test_budget_report():
    state = {"usage": {"queries": 2}}
    profile = {"max_queries": 8, "max_pages": 10, "max_evidence_cards": 10, "estimated_input_tokens": 100, "estimated_output_tokens": 100}
    assert report(state, profile)["remaining"]["queries"] == 6


def test_canonical_url_removes_tracking():
    assert canonical_url("HTTPS://Example.com/a/?utm_source=x&b=2#top") == "https://example.com/a?b=2"


def test_ingest_worker_deduplicates(tmp_path):
    path = tmp_path / "cards.jsonl"
    result = {"question_id": "q-001", "evidence_cards": [{"source": {"url": "https://example.com/a?utm_source=x"}, "statement": "A fact", "stance": "support", "confidence": 0.8}, {"source": {"url": "https://example.com/a"}, "statement": "A fact", "stance": "support", "confidence": 0.8}]}
    outcome = ingest_worker_result(path, result, max_new=3)
    assert outcome["accepted"] == 1
    assert outcome["duplicates"] == 1
    assert len(path.read_text().splitlines()) == 1


def test_tool_registry_valid():
    registry = load_registry(SCRIPT_DIR.parent / "config/tools.toml")
    assert validate_registry(registry) == []
    assert resolve(registry, "repo_read")[0]["name"] == "github_mcp"
