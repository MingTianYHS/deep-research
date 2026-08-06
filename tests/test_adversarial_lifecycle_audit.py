import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import lib.agent_contracts as contracts
import lib.completion as completion
from lib.agent_snapshots import build_review_snapshot, canonical_sha256
from lib.critic_reviews import save_review


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def minimal_snapshot_root(tmp_path: Path) -> Path:
    root = tmp_path / "主题"
    for relative in ("plans", "logs/workers", "logs/critic_reviews", "evidence", "reports"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    write_json(root / "plans/current-design.json", {"questions": []})
    (root / "evidence/cards.jsonl").write_text("", encoding="utf-8")
    (root / "claims.jsonl").write_text("", encoding="utf-8")
    (root / "topic.toml").write_text('language = "zh-CN"\n', encoding="utf-8")
    return root


@pytest.mark.xfail(strict=True, reason="completion gate currently permits complete Runs without Claim–Evidence")
def test_complete_run_must_require_current_run_claim_evidence(monkeypatch, tmp_path):
    root = minimal_snapshot_root(tmp_path)
    card = {"id": "ev-1", "question_id": "q-1"}
    (root / "evidence/cards.jsonl").write_text(json.dumps(card) + "\n", encoding="utf-8")
    write_json(
        root / "logs/workers/worker-1.json",
        {"worker_result_id": "worker-1", "run_id": "run-1", "status": "complete", "ingest_summary": {"accepted_evidence_ids": ["ev-1"]}},
    )
    report = root / "reports/final.md"
    report.write_text("Result [[ev-1]]", encoding="utf-8")
    write_json(root / "reports/final.md.audit.json", {"run_id": "run-1", "report": str(report)})
    monkeypatch.setattr(completion, "approved_reviews_for_run", lambda *_args, **_kwargs: [{"id": "critic-1"}])
    monkeypatch.setattr(completion, "_quality", lambda *_args, **_kwargs: {"passes_all_gates": True})
    monkeypatch.setattr(completion, "load_rubric", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(completion, "verify_report", lambda *_args, **_kwargs: {"valid": True})
    monkeypatch.setattr(completion, "validate_audit", lambda *_args, **_kwargs: {"valid": True})
    monkeypatch.setattr(completion, "evaluate_report", lambda *_args, **_kwargs: {"passes_all_gates": True})
    result = completion.completion_gate(root, "run-1", SCRIPT_DIR.parent)
    assert not result["valid"]
    assert any("Claim" in error for error in result["errors"])


@pytest.mark.xfail(strict=True, reason="review snapshot currently retains accepted Evidence IDs whose cards are missing")
def test_review_snapshot_must_fail_closed_on_missing_evidence_card(tmp_path):
    root = minimal_snapshot_root(tmp_path)
    write_json(
        root / "logs/workers/worker-1.json",
        {"worker_result_id": "worker-1", "run_id": "run-1", "status": "complete", "ingest_summary": {"accepted_evidence_ids": ["ev-missing"]}},
    )
    snapshot = build_review_snapshot(root, "run-1")
    assert "ev-missing" not in snapshot["evidence_ids"]


def synthesis_fixture(monkeypatch, tmp_path):
    root = minimal_snapshot_root(tmp_path)
    report_a = root / "reports/目标报告.md"
    report_b = root / "reports/其他报告.md"
    report_a.write_text("待补充", encoding="utf-8")
    report_b.write_text("待补充", encoding="utf-8")
    current = {
        "snapshot_version": 1,
        "run_id": "run-1",
        "design_sha256": "d",
        "worker_results_sha256": "w",
        "evidence_sha256": "e",
        "claims_sha256": "c",
        "worker_result_ids": [],
        "evidence_ids": [],
        "claim_ids": [],
    }
    review = {"id": "critic-1", "run_id": "run-1", "status": "approved", "reviewed_snapshot": current}
    monkeypatch.setattr(contracts, "build_review_snapshot", lambda *_args: current)
    monkeypatch.setattr(contracts, "load_review", lambda *_args: review)
    assignment = contracts.build_synthesis_assignment(root, "run-1", report_a, review)
    return root, report_a, report_b, review, assignment


@pytest.mark.xfail(strict=True, reason="SynthesisResult is not bound to the exact report_path from its Assignment")
def test_synthesis_must_write_only_the_assigned_report(monkeypatch, tmp_path):
    root, _report_a, report_b, _review, assignment = synthesis_fixture(monkeypatch, tmp_path)
    value = {
        "synthesis_result_version": 1,
        "id": "synthesis-1",
        "run_id": "run-1",
        "critic_review_id": "critic-1",
        "input_snapshot": assignment["input_snapshot"],
        "status": "partial",
        "report_path": str(report_b),
        "output_language": "zh-CN",
        "claim_ids_used": [],
        "evidence_ids_used": [],
        "unresolved": [],
        "report_markdown": "Partial report",
    }
    result = contracts.validate_synthesis_result(root, value, "run-1")
    assert not result["valid"]
    assert any("assigned report" in error for error in result["errors"])


@pytest.mark.xfail(strict=True, reason="blocked SynthesisResult currently requires unused report Markdown")
def test_blocked_synthesis_may_omit_report_markdown(monkeypatch, tmp_path):
    root, report_a, _report_b, _review, assignment = synthesis_fixture(monkeypatch, tmp_path)
    value = {
        "synthesis_result_version": 1,
        "id": "synthesis-blocked",
        "run_id": "run-1",
        "critic_review_id": "critic-1",
        "input_snapshot": assignment["input_snapshot"],
        "status": "blocked",
        "report_path": str(report_a),
        "output_language": "zh-CN",
        "claim_ids_used": [],
        "evidence_ids_used": [],
        "unresolved": ["Missing Evidence"],
        "report_markdown": "",
    }
    result = contracts.validate_synthesis_result(root, value, "run-1")
    assert result["valid"], result["errors"]


@pytest.mark.xfail(strict=True, reason="Critic reviewed_at is currently accepted from Agent input instead of server-owned")
def test_critic_review_timestamp_must_be_server_owned(tmp_path):
    root = minimal_snapshot_root(tmp_path)
    snapshot = build_review_snapshot(root, "run-1")
    supplied = "2999-01-01T00:00:00Z"
    outcome = save_review(
        root,
        {
            "critic_review_version": 2,
            "id": "critic-future",
            "run_id": "run-1",
            "reviewed_by": "research_critic",
            "reviewed_snapshot": snapshot,
            "reviewed_at": supplied,
            "status": "approved",
            "findings": [],
            "targeted_searches": [],
            "unresolved": [],
            "stop_reason": "review_complete",
        },
        "run-1",
    )
    assert outcome["critic_review"]["reviewed_at"] != supplied
