import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from lib.claims import create, link
from lib.io_utils import atomic_write_json
from lib.research_memory import build_reuse_plan, persist_knowledge_update, validate_next_research


def topic(tmp_path: Path) -> Path:
    root = tmp_path / "topic"
    for relative in ("plans", "logs/workers", "evidence", "memory"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    atomic_write_json(root / "state.json", {"baseline_completed": True, "last_run_at": "2026-08-01T00:00:00Z", "knowledge_status": "evolving"})
    (root / "claims.jsonl").write_text("", encoding="utf-8")
    card = {"id": "ev-1", "question_id": "q-001", "source_attempt_id": "src-1", "source": {"url": "https://example.com/report", "canonical_url": "https://example.com/report", "title": "Report", "publisher": "Example", "source_type": "official", "accessed_at": "2026-08-01T00:00:00Z"}, "statement": "Existing fact", "stance": "support", "confidence": 0.9, "ingested_at": "2026-08-01T00:00:00Z"}
    (root / "evidence/cards.jsonl").write_text(json.dumps(card) + "\n", encoding="utf-8")
    (root / "logs/source_attempts.jsonl").write_text(json.dumps({"id": "src-1", "normalized_url": "https://example.com/report", "content_sha256": "a" * 64, "status": "accepted"}) + "\n", encoding="utf-8")
    atomic_write_json(root / "logs/workers/worker-1.json", {"run_id": "run-old", "question_id": "q-001", "queries_run": [{"query": "existing query", "intent": "primary_source", "provider": "native_web", "time_anchor": "2026", "outcome": "primary_candidate_found"}]})
    claim = create(root / "claims.jsonl", "Existing fact", 0.9, False)
    link(root / "claims.jsonl", claim["id"], "ev-1", "support", 0.9)
    return root


def test_reuse_plan_recalls_evidence_sources_queries_and_claims(tmp_path):
    plan = build_reuse_plan(topic(tmp_path), "q-001")
    assert plan["research_mode"] == "incremental"
    assert plan["existing_evidence"][0]["id"] == "ev-1"
    assert plan["known_sources"][0]["content_sha256"] == "a" * 64
    assert plan["prior_queries"][0]["query"] == "existing query"
    assert plan["relevant_claims"]
    assert plan["recommended_action"] in {"reuse_existing_evidence_before_search", "refresh_known_sources_before_search"}


def test_persisted_knowledge_delta_updates_backlog_and_bounded_memory(tmp_path):
    root = topic(tmp_path)
    delta = {"new_claims": [], "strengthened_claims": ["cl-1"], "weakened_claims": [], "new_connections": [], "new_hypotheses": [], "remaining_gaps": ["Need current data"]}
    backlog = [{"id": "rq-1", "question": "What changed?", "reason": "Current data is missing", "priority": "high", "gap_type": "freshness", "known_evidence_ids": ["ev-1"], "acceptance_criteria": ["Find a current primary source"]}]
    result = persist_knowledge_update(root, "run-1", delta, backlog)
    assert result["backlog_items"] == 1
    assert (root / "plans/research-backlog.json").exists()
    assert (root / "memory/current.md").exists()
    assert "What changed?" in (root / "memory/current.md").read_text(encoding="utf-8")


def test_backlog_is_bounded():
    item = {"id": "rq", "question": "Q", "reason": "R", "priority": "low", "gap_type": "gap", "known_evidence_ids": [], "acceptance_criteria": ["A"]}
    assert any("at most" in error for error in validate_next_research([{**item, "id": f"rq-{index}"} for index in range(6)]))
