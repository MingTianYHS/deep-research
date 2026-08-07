import importlib.util,json
from pathlib import Path
import pytest
SCRIPT=Path(__file__).parents[1]/".agents/skills/deep-research/scripts/researchctl.py";spec=importlib.util.spec_from_file_location("researchctl",SCRIPT);module=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(module)
def test_slugify_ascii():assert module.slugify("AI Market Research")=="ai-market-research"
def test_slugify_chinese():assert module.slugify("AI 短剧 行业")=="ai-短剧-行业"
def test_budget_profiles_exist_and_question_limits_align():
    b=module.load_budgets();assert b["standard"]["max_workers"]<=5;assert b["deep"]["max_questions"]==8;assert "estimated_input_tokens" not in b["standard"]
def init(module,tmp_path):
    module.WORKSPACE_ROOT=tmp_path;args=type("A",(),{"title":"主题","slug":"topic","budget":"lite","force":False,"install_agent":False})();module.cmd_init(args);return tmp_path/"topic"
def test_init_creates_topic_expert_workspace(monkeypatch,tmp_path):
    root=init(module,tmp_path);state=json.loads((root/"state.json").read_text(encoding="utf-8"));assert state["workspace_format_version"]==2;assert not state["baseline_completed"];assert state["research_generation"]==0;assert state["context_generated_at"];assert state["usage"]=={"queries":0,"pages":0,"evidence_cards":0};assert (root/"AGENTS.md").exists();assert not (root/"AGENT.md").exists();assert (root/"context.md").exists();assert (root/"memory/lessons.jsonl").exists();assert not (root/"tasks.jsonl").exists();assert not (root/"source_map.md").exists();assert not (root/"evidence/raw").exists();assert not (root/"cache").exists();monkeypatch.chdir(root);assert module.topic_dir()==root.resolve()
def test_plan_uses_one_canonical_design_and_syncs_without_overwrite(tmp_path):
    root=init(module,tmp_path);args=type("A",(),{"slug":"topic","questions":3,"force":False})();module.cmd_plan(args);path=root/"plans/current-design.json";design=json.loads(path.read_text(encoding="utf-8"));design["questions"][0]["question"]="edited question";path.write_text(json.dumps(design),encoding="utf-8");module.cmd_plan(args);synced=json.loads(path.read_text(encoding="utf-8"));state=json.loads((root/"state.json").read_text(encoding="utf-8"));assert synced["questions"][0]["question"]=="edited question";assert state["open_questions"]==["q-001","q-002","q-003"];assert "edited question" in (root/"questions.md").read_text(encoding="utf-8")
def test_lite_plan_rejects_more_than_four_questions(tmp_path):
    init(module,tmp_path);args=type("A",(),{"slug":"topic","questions":5,"force":False})();
    with pytest.raises(SystemExit,match="allows 1-4"):module.cmd_plan(args)
def test_legacy_cli_does_not_expose_guarded_writes():
    root=module.parser();subparsers=next(action for action in root._actions if action.dest=="command");assert "init-topic" not in subparsers.choices;assert "report-init" not in subparsers.choices;assert "record-usage" not in subparsers.choices;assert "estimate" not in subparsers.choices
