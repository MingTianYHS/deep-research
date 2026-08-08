import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from lib.evidence import ingest_worker_result
from lib.io_utils import atomic_write_json
from lib.worker_contract import profile_limits, validate_worker_result
from lib.worker_context import validate_ingest_context


def result(profile="standard"):
    return {"worker_result_version": 2, "worker_result_id": "worker-reuse", "run_id": "run-2", "status": "complete", "question_id": "q-001", "overlap_key": "market", "budget_profile": profile, "coverage_status": "sufficient", "queries_run": [], "source_attempts": [], "evidence_cards": [], "reused_evidence_ids": ["ev-old"], "gaps": [], "budget_used": {"tool_calls": 0, "search_queries": 0, "source_pages": 0}, "stop_reason": "existing_evidence_sufficient"}


def root(tmp_path: Path) -> Path:
    value = tmp_path / "topic"
    for relative in ("plans", "logs/workers", "evidence"):
        (value / relative).mkdir(parents=True, exist_ok=True)
    atomic_write_json(value / "state.json", {"active_run_id": "run-2", "budget_profile": "standard"})
    atomic_write_json(value / "plans/current-design.json", {"questions": [{"id": "q-001", "status": "open", "overlap_key": "market", "worker_budget_profile": "standard", "version_sensitive": False}]})
    card = {"id": "ev-old", "question_id": "q-001", "source_attempt_id": "src-old", "source": {"url": "https://example.com", "canonical_url": "https://example.com"}, "statement": "Existing fact", "stance": "support", "confidence": 0.9, "quote": "Existing fact", "independence_group": "example", "prompt_injection_risk": "low", "version_compatibility": "not_applicable"}
    (value / "evidence/cards.jsonl").write_text(json.dumps(card) + "\n", encoding="utf-8")
    (value / "logs/source_attempts.jsonl").write_text("", encoding="utf-8")
    return value


def test_standard_worker_can_complete_by_reusing_evidence():
    checked = validate_worker_result(result(), profile_limits("standard"))
    assert checked["valid"], checked["errors"]
    assert checked["reuse_only"]


def test_deep_worker_cannot_complete_by_reuse_only():
    value = result("deep")
    checked = validate_worker_result(value, profile_limits("deep"))
    assert not checked["valid"]
    assert any("deep" in error for error in checked["errors"])


def test_reused_evidence_is_bound_to_question_and_persisted_for_run(tmp_path):
    topic = root(tmp_path)
    checked = validate_ingest_context(topic, result())
    assert checked["valid"], checked["errors"]
    outcome = ingest_worker_result(topic / "evidence/cards.jsonl", result(), 10)
    assert outcome["accepted"] == 0
    assert outcome["reused_ids"] == ["ev-old"]
    logged = json.loads((topic / "logs/workers/worker-reuse.json").read_text(encoding="utf-8"))
    assert logged["ingest_summary"]["accepted_evidence_ids"] == ["ev-old"]


def test_historical_query_repeat_requires_reason(tmp_path):
    topic = root(tmp_path)
    atomic_write_json(topic / "logs/workers/worker-old.json", {"run_id": "run-1", "queries_run": [{"query": "same query", "intent": "primary_source"}]})
    value = result(); value.update(status="partial", coverage_status="partial", reused_evidence_ids=[], stop_reason="gap_recorded")
    value["queries_run"] = [{"id": "q-2", "query": "same query", "intent": "primary_source", "provider": "native_web", "language": "en", "fallback_of": None, "outcome": "low_yield"}]
    value["budget_used"] = {"tool_calls": 1, "search_queries": 1, "source_pages": 0}
    checked = validate_ingest_context(topic, value)
    assert not checked["valid"]
    value["queries_run"][0]["repeat_reason"] = "stale_refresh"
    checked = validate_ingest_context(topic, value)
    assert checked["valid"], checked["errors"]
