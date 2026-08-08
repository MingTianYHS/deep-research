import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import lib.lean_workflow as lean


def prepare(root: Path, profile: str, workers=None):
    (root / "logs/workers").mkdir(parents=True); (root / "state.json").write_text(json.dumps({"budget_profile": profile, "active_run_id": "run-1"}), encoding="utf-8"); (root / "config").mkdir(); (root / "config/orchestration.toml").write_text("""
[lite]
max_next_calls_per_run=25
max_same_action_repeats=2
max_critic_reviews=1
max_targeted_searches=1
[standard]
max_next_calls_per_run=45
max_same_action_repeats=3
max_critic_reviews=1
max_targeted_searches=2
[deep]
max_next_calls_per_run=100
max_same_action_repeats=8
max_critic_reviews=4
max_targeted_searches=3
""", encoding="utf-8")
    for index, worker in enumerate(workers or []): (root / f"logs/workers/w{index}.json").write_text(json.dumps(worker), encoding="utf-8")


def action(reuse=False):
    plan = {"recommended_action": "reuse_existing_evidence_before_search" if reuse else "targeted_discovery"}
    return {"phase": "worker_research", "next_action": "delegate_open_questions", "agent": "topic_researcher", "assignments": [{"question_id": "q-002", "disconfirming_query": "q2 negative", "remediation": None, "reuse_plan": plan}, {"question_id": "q-001", "disconfirming_query": "q1 negative", "remediation": None, "reuse_plan": plan}], "progress": {}}


def test_standard_dispatches_one_run_level_disconfirmation(monkeypatch, tmp_path):
    prepare(tmp_path, "standard"); monkeypatch.setattr(lean, "derive_strict_workflow", lambda *_: action()); result = lean.derive_workflow(tmp_path, tmp_path); by_id = {item["question_id"]: item for item in result["assignments"]}; assert by_id["q-001"]["disconfirming_required"] is True; assert by_id["q-002"]["disconfirming_required"] is False; assert by_id["q-002"]["disconfirming_query"] is None


def test_standard_reuse_only_run_skips_disconfirmation(monkeypatch, tmp_path):
    prepare(tmp_path, "standard"); monkeypatch.setattr(lean, "derive_strict_workflow", lambda *_: action(reuse=True)); result = lean.derive_workflow(tmp_path, tmp_path); assert not any(item["disconfirming_required"] for item in result["assignments"])


def test_standard_does_not_repeat_disconfirmation(monkeypatch, tmp_path):
    prepare(tmp_path, "standard", [{"run_id": "run-1", "queries_run": [{"intent": "disconfirming"}]}]); monkeypatch.setattr(lean, "derive_strict_workflow", lambda *_: action()); result = lean.derive_workflow(tmp_path, tmp_path); assert not any(item["disconfirming_required"] for item in result["assignments"])


def test_lite_skips_routine_disconfirmation(monkeypatch, tmp_path):
    prepare(tmp_path, "lite"); monkeypatch.setattr(lean, "derive_strict_workflow", lambda *_: action()); result = lean.derive_workflow(tmp_path, tmp_path); assert not any(item["disconfirming_required"] for item in result["assignments"])


def test_deep_preserves_strict_assignments(monkeypatch, tmp_path):
    prepare(tmp_path, "deep"); expected = action(); monkeypatch.setattr(lean, "derive_strict_workflow", lambda *_: expected); assert lean.derive_workflow(tmp_path, tmp_path) is expected
