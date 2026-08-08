import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts/researchctl.py"
spec = importlib.util.spec_from_file_location("researchctl", SCRIPT)
module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)


def test_slugify_ascii(): assert module.slugify("AI Market Research") == "ai-market-research"
def test_slugify_chinese(): assert module.slugify("AI 短剧 行业") == "ai-短剧-行业"


def test_budget_profiles_exist_and_question_limits_align():
    budgets = module.load_budgets(); assert budgets["standard"]["max_workers"] <= 5; assert budgets["deep"]["max_questions"] == 8; assert "estimated_input_tokens" not in budgets["standard"]


def init(module, tmp_path):
    module.WORKSPACE_ROOT = tmp_path; args = type("A", (), {"title": "主题", "slug": "topic", "budget": "lite", "force": False, "install_agent": False})(); module.cmd_init(args); return tmp_path / "topic"


def test_init_creates_research_assistant_workspace(monkeypatch, tmp_path):
    root = init(module, tmp_path); state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    assert state["workspace_format_version"] == 3; assert not state["baseline_completed"]; assert state["active_run_scope"] is None; assert state["context_generated_at"]
    assert state["usage"] == {"queries": 0, "pages": 0, "evidence_cards": 0}; assert state["lifetime_usage"] == state["usage"]
    assert (root / "AGENTS.md").exists(); assert "不是无限自主循环" in (root / "AGENTS.md").read_text(encoding="utf-8")
    assert (root / "context.md").exists(); assert (root / "memory/current.md").exists(); assert (root / "plans/research-backlog.json").exists(); assert (root / "memory/knowledge-deltas.jsonl").exists(); assert (root / "plans/history").is_dir()
    assert not (root / "AGENT.md").exists(); assert not (root / "tasks.jsonl").exists(); assert not (root / "source_map.md").exists(); assert not (root / "evidence/raw").exists(); assert not (root / "cache").exists(); assert not (root / "logs/change_log.md").exists()
    monkeypatch.chdir(root); assert module.topic_dir() == root.resolve()


def test_plan_uses_one_canonical_design_and_syncs_without_overwrite(tmp_path):
    root = init(module, tmp_path); args = type("A", (), {"slug": "topic", "questions": 3, "force": False})(); module.cmd_plan(args); path = root / "plans/current-design.json"; design = json.loads(path.read_text(encoding="utf-8")); design["questions"][0]["question"] = "edited question"; path.write_text(json.dumps(design), encoding="utf-8"); module.cmd_plan(args)
    synced = json.loads(path.read_text(encoding="utf-8")); state = json.loads((root / "state.json").read_text(encoding="utf-8")); assert synced["questions"][0]["question"] == "edited question"; assert synced["design_mode"] == "baseline"; assert state["open_questions"] == ["q-001", "q-002", "q-003"]; assert "edited question" in (root / "questions.md").read_text(encoding="utf-8")


def test_lite_plan_rejects_more_than_four_questions(tmp_path):
    init(module, tmp_path); args = type("A", (), {"slug": "topic", "questions": 5, "force": False})()
    with pytest.raises(SystemExit, match="allows 1-4"): module.cmd_plan(args)


def test_start_requires_a_valid_design(tmp_path):
    init(module, tmp_path)
    with pytest.raises(SystemExit, match="current-design"): module.cmd_run_start(type("A", (), {"slug": "topic", "mode": "initial"})())


def test_complete_baseline_then_continue_creates_scoped_incremental_run(monkeypatch, tmp_path):
    root = init(module, tmp_path); module.cmd_plan(type("A", (), {"slug": "topic", "questions": 1, "force": False})())
    state = json.loads((root / "state.json").read_text(encoding="utf-8")); state["usage"] = {"queries": 4, "pages": 3, "evidence_cards": 2}; state["lifetime_usage"] = dict(state["usage"]); (root / "state.json").write_text(json.dumps(state), encoding="utf-8")
    module.cmd_run_start(type("A", (), {"slug": "topic", "mode": "initial"})()); started = json.loads((root / "state.json").read_text(encoding="utf-8")); assert started["active_run_scope"]["mode"] == "baseline"; assert started["active_run_scope"]["assigned_question_ids"] == ["q-001"]; assert started["usage"] == {"queries": 0, "pages": 0, "evidence_cards": 0}; assert started["lifetime_usage"] == {"queries": 4, "pages": 3, "evidence_cards": 2}
    monkeypatch.setattr(module, "completion_gate", lambda *_args: {"valid": True, "errors": []}); module.cmd_run_finish(type("A", (), {"slug": "topic", "status": "complete", "note": ""})())
    finished = json.loads((root / "state.json").read_text(encoding="utf-8")); assert finished["baseline_completed"] is True; assert finished["last_completed_run_id"]; assert finished["active_run_id"] is None; assert finished["active_run_scope"] is None; assert finished["open_questions"] == []
    module.cmd_continue(type("A", (), {"slug": "topic", "backlog_id": None, "question": "海外市场如何变化？"})()); second = json.loads((root / "state.json").read_text(encoding="utf-8")); assert second["active_run_scope"]["mode"] == "incremental"; assert len(second["active_run_scope"]["assigned_question_ids"]) == 1; assert second["usage"] == {"queries": 0, "pages": 0, "evidence_cards": 0}
    design = json.loads((root / "plans/current-design.json").read_text(encoding="utf-8")); assert design["design_mode"] == "incremental"; assert design["questions"][0]["question"] == "海外市场如何变化？"; assert list((root / "plans/history").glob("design-*.json"))


def test_legacy_cli_does_not_expose_guarded_writes():
    root = module.parser(); subparsers = next(action for action in root._actions if action.dest == "command"); assert "init-topic" not in subparsers.choices; assert "report-init" not in subparsers.choices; assert "record-usage" not in subparsers.choices; assert "estimate" not in subparsers.choices
