import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import lib.completion as completion
from lib.audit import create_audit
from lib.critic_reviews import validate_review
from lib.evidence import ingest_worker_result
from lib.research_memory import latest_verifications, validate_knowledge_delta, validate_next_research
from lib.worker_contract import profile_limits, validate_worker_result
from tests.test_critic_reviews import base_review
from tests.test_runtime import prepare_topic, worker_result


def test_audit_uses_latest_valid_verification_and_ignores_failed_refresh(tmp_path):
    root = tmp_path / "topic"
    (root / "evidence").mkdir(parents=True)
    (root / "logs").mkdir()
    card = {"id": "ev-1", "source_attempt_id": "src-1", "source": {"url": "https://example.com/report"}, "statement": "Fact", "quote": "Fact"}
    attempts = [
        {"id": "src-1", "url": "https://example.com/report", "normalized_url": "https://example.com/report", "status": "accepted", "eligible_for_evidence": True, "content_sha256": "a" * 64},
        {"id": "src-2", "url": "https://example.com/report", "normalized_url": "https://example.com/report", "status": "accepted", "eligible_for_evidence": True, "content_sha256": "b" * 64},
        {"id": "src-3", "url": "https://example.com/report", "normalized_url": "https://example.com/report", "status": "unavailable", "eligible_for_evidence": False, "content_sha256": None},
    ]
    (root / "logs/source_attempts.jsonl").write_text("\n".join(json.dumps(item) for item in attempts) + "\n")
    verifications = [
        {"id": "ver-2", "evidence_id": "ev-1", "source_attempt_id": "src-2", "verified_at": "2026-08-09T00:00:00Z", "content_sha256": "b" * 64, "status": "revalidated"},
        {"id": "ver-3", "evidence_id": "ev-1", "source_attempt_id": "src-3", "verified_at": "2026-08-09T01:00:00Z", "content_sha256": None, "result": "not_found", "statement_still_supported": False},
    ]
    (root / "evidence/verifications.jsonl").write_text("\n".join(json.dumps(item) for item in verifications) + "\n")
    effective = latest_verifications(root)
    assert effective["ev-1"]["id"] == "ver-2"
    report = root / "report.md"
    report.write_text("Fact [[ev-1]]")
    output = root / "audit.json"
    create_audit(report, {"ev-1": card}, output, {item["id"]: item for item in attempts}, verifications=effective)
    item = json.loads(output.read_text())["items"][0]
    assert item["evidence_version"] == "verification"
    assert item["expected_source_attempt_id"] == "src-2"
    assert item["expected_content_sha256"] == "b" * 64


def test_targeted_recheck_cannot_open_new_findings_or_searches():
    review = base_review()
    review.update(review_mode="targeted_recheck", previous_review_id="critic-0", reviewed_finding_ids=["finding-1"], targeted_searches=[], unresolved=["finding-1"])
    contract = {"review_mode": "targeted_recheck", "previous_review_id": "critic-0", "allowed_finding_ids": ["finding-1"]}
    assert validate_review(review, expected_contract=contract)["valid"]
    review["findings"][0]["id"] = "finding-new"
    checked = validate_review(review, expected_contract=contract)
    assert not checked["valid"]
    assert any("allowed Finding IDs" in error for error in checked["errors"])
    review["findings"][0]["id"] = "finding-1"
    review["targeted_searches"] = base_review()["targeted_searches"]
    assert any("may not request new searches" in error for error in validate_review(review, expected_contract=contract)["errors"])


def test_complete_requires_every_assigned_question(monkeypatch, tmp_path):
    root = tmp_path / "topic"
    (root / "reports").mkdir(parents=True)
    (root / "state.json").write_text(json.dumps({"active_run_id": "run-1", "active_run_scope": {"run_id": "run-1", "assigned_question_ids": [f"q-{index}" for index in range(1, 7)]}}))
    workers = [{"status": "complete", "question_id": f"q-{index}", "ingest_summary": {"accepted_evidence_ids": [f"ev-{index}"]}} for index in range(1, 6)]
    monkeypatch.setattr(completion, "_workers", lambda *_: workers)
    monkeypatch.setattr(completion, "_evidence", lambda *_: {f"ev-{index}": {"id": f"ev-{index}"} for index in range(1, 6)})
    monkeypatch.setattr(completion, "approved_reviews_for_run", lambda *_: [{"id": "critic-1"}])
    monkeypatch.setattr(completion, "_quality", lambda *_args, **_kwargs: {"passes_all_gates": True})
    monkeypatch.setattr(completion, "load_rubric", lambda *_: {})
    result = completion.completion_gate(root, "run-1", tmp_path / "skill")
    assert not result["valid"]
    assert any("q-6" in error for error in result["errors"])


def test_ingest_rejects_conflicting_source_attempt_id(tmp_path):
    cards = tmp_path / "topic/evidence/cards.jsonl"
    cards.parent.mkdir(parents=True)
    cards.write_text("")
    prepare_topic(cards)
    ingest_worker_result(cards, worker_result(), 3)
    state_path = tmp_path / "topic/state.json"
    state = json.loads(state_path.read_text())
    state["active_run_id"] = "run-2"
    state["active_run_scope"] = {"run_id": "run-2", "assigned_question_ids": ["q-001"]}
    state_path.write_text(json.dumps(state))
    conflicting = worker_result()
    conflicting.update(worker_result_id="worker-2", run_id="run-2")
    for query in conflicting["queries_run"]:
        query["repeat_reason"] = "scope_changed"
    conflicting["source_attempts"][0].update(url="https://example.com/b", normalized_url="https://example.com/b", content_sha256="b" * 64)
    conflicting["evidence_cards"][0]["source"]["url"] = "https://example.com/b"
    conflicting["evidence_cards"][0]["statement"] = "Different fact"
    try:
        ingest_worker_result(cards, conflicting, 3)
        assert False
    except ValueError as exc:
        assert "Source Attempt id conflict" in str(exc)


def test_worker_and_memory_payloads_are_bounded():
    result = worker_result()
    duplicate = dict(result["queries_run"][0])
    duplicate["id"] = "query-duplicate"
    result["queries_run"].append(duplicate)
    result["budget_used"]["search_queries"] += 1
    checked = validate_worker_result(result, profile_limits("standard"))
    assert any("duplicates a query" in error for error in checked["errors"])
    delta = {key: [] for key in ("new_claims", "strengthened_claims", "weakened_claims", "new_connections", "new_hypotheses", "remaining_gaps")}
    delta["remaining_gaps"] = ["x" * 501]
    assert any("500" in error for error in validate_knowledge_delta(delta))
    backlog = [{"id": "rq-1", "question": "x" * 501, "reason": "reason", "priority": "high", "gap_type": "freshness", "known_evidence_ids": [], "acceptance_criteria": ["criterion"]}]
    assert any("question" in error for error in validate_next_research(backlog))
