import argparse
import contextlib
import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from lib.synthesis_store import persist_knowledge_update

SPEC = importlib.util.spec_from_file_location("agentctl_test", SCRIPT_DIR / "agentctl.py")
agentctl = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(agentctl)


def prepare(tmp_path: Path) -> Path:
    root = tmp_path / "topic"
    for relative in ("memory", "plans", "logs/syntheses", "reports", "evidence"): (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "claims.jsonl").write_text(""); (root / "evidence/cards.jsonl").write_text(""); (root / "logs/source_attempts.jsonl").write_text(""); (root / "memory/knowledge-deltas.jsonl").write_text("")
    (root / "state.json").write_text(json.dumps({"active_run_id": "run-1"})); return root


def delta(): return {"new_claims": [], "strengthened_claims": [], "weakened_claims": [], "new_connections": [], "new_hypotheses": [], "remaining_gaps": []}


def test_knowledge_update_is_idempotent_by_synthesis_id(tmp_path):
    root = prepare(tmp_path); first = persist_knowledge_update(root, "run-1", "syn-1", delta(), []); second = persist_knowledge_update(root, "run-1", "syn-1", delta(), [])
    assert first["knowledge_delta_recorded"]; assert second["knowledge_delta_already_recorded"]
    assert len((root / "memory/knowledge-deltas.jsonl").read_text().splitlines()) == 1
    backlog = json.loads((root / "plans/research-backlog.json").read_text()); assert backlog["generated_from_synthesis"] == "syn-1"


def test_blocked_synthesis_is_logged_but_does_not_replace_memory(monkeypatch, tmp_path, capsys):
    root = prepare(tmp_path); report = root / "reports/final.md"
    value = {"synthesis_result_version": 2, "id": "syn-blocked", "run_id": "run-1", "critic_review_id": "critic-1", "input_snapshot": {}, "status": "blocked", "report_path": str(report), "output_language": "zh-CN", "claim_ids_used": [], "evidence_ids_used": [], "unresolved": ["missing evidence"], "knowledge_delta": delta(), "next_research": [], "report_markdown": "Blocked"}
    source = root / "result.json"; source.write_text(json.dumps(value)); monkeypatch.setattr(agentctl.researchctl, "topic_dir", lambda _topic: root); monkeypatch.setattr(agentctl.researchctl, "lock", lambda _root: contextlib.nullcontext()); monkeypatch.setattr(agentctl, "validate_synthesis_result", lambda *_args: {"valid": True, "errors": []})
    args = argparse.Namespace(topic=None, file=str(source)); agentctl.cmd_synthesis_save(args); first = json.loads(capsys.readouterr().out)
    assert first["status"] == "blocked"; assert not first["memory_applied"]; assert not report.exists(); assert not (root / "plans/research-backlog.json").exists(); assert not (root / "memory/knowledge-deltas.jsonl").read_text()
    agentctl.cmd_synthesis_save(args); second = json.loads(capsys.readouterr().out); assert second["idempotent"] is True
