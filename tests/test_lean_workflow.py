import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import lib.lean_workflow as lean
from lib.audit import create_audit, mechanically_verify_audit, validate_audit


def write_state(root: Path, profile: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "state.json").write_text(
        json.dumps({"budget_profile": profile}), encoding="utf-8"
    )


def test_standard_defers_reflection(monkeypatch, tmp_path):
    write_state(tmp_path, "standard")
    monkeypatch.setattr(
        lean,
        "derive_strict_workflow",
        lambda *_args: {
            "phase": "reflection_blocked",
            "next_action": "report_missing_run_critic_review",
            "command": None,
            "agent": None,
            "blockers": ["missing review"],
            "assignments": [],
            "progress": {"run_id": "run-old"},
        },
    )
    result = lean.derive_workflow(tmp_path, tmp_path)
    assert result["phase"] == "ready_to_start"
    assert result["next_action"] == "start_run"
    assert result["progress"]["deferred_reflection_run_id"] == "run-old"


def test_standard_replaces_second_critic_with_mechanical_audit(monkeypatch, tmp_path):
    write_state(tmp_path, "standard")
    monkeypatch.setattr(
        lean,
        "derive_strict_workflow",
        lambda *_args: {
            "phase": "report_audit",
            "next_action": "initialize_quote_audit",
            "command": "qualityctl.py audit-init",
            "agent": "research_critic",
            "blockers": [],
            "assignments": [],
            "progress": {"report": "/tmp/report.md"},
        },
    )
    result = lean.derive_workflow(tmp_path, tmp_path)
    assert result["next_action"] == "run_mechanical_lineage_audit"
    assert result["agent"] is None
    assert "audit-mechanical" in result["command"]


def test_deep_keeps_strict_workflow(monkeypatch, tmp_path):
    write_state(tmp_path, "deep")
    expected = {
        "phase": "report_audit",
        "next_action": "initialize_quote_audit",
        "progress": {"report": "/tmp/report.md"},
    }
    monkeypatch.setattr(lean, "derive_strict_workflow", lambda *_args: expected)
    assert lean.derive_workflow(tmp_path, tmp_path) is expected


def test_mechanical_audit_is_explicit_and_final_valid(tmp_path):
    report = tmp_path / "report.md"
    report.write_text("Fact [[ev-1]]", encoding="utf-8")
    output = tmp_path / "report.md.audit.json"
    evidence = {
        "ev-1": {
            "id": "ev-1",
            "source_attempt_id": "sa-1",
            "source": {"url": "https://example.com"},
            "statement": "Fact",
            "quote": "Exact quote",
            "locator": "Section 1",
        }
    }
    attempts = {
        "sa-1": {
            "id": "sa-1",
            "status": "accepted",
            "eligible_for_evidence": True,
            "content_sha256": "a" * 64,
        }
    }
    create_audit(report, evidence, output, attempts, run_id="run-1")
    mechanically_verify_audit(output)
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["verification_mode"] == "mechanical_lineage"
    assert stored["items"][0]["checked_by"] == "qualityctl:mechanical"
    assert stored["items"][0]["match_type"] == "lineage_only"
    assert validate_audit(output, require_all_verified=True)["valid"]
