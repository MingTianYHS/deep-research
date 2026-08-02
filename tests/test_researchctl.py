import importlib.util,json
from pathlib import Path
SCRIPT=Path(__file__).parents[1]/".agents/skills/deep-research/scripts/researchctl.py";spec=importlib.util.spec_from_file_location("researchctl",SCRIPT);module=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(module)
def test_slugify_ascii():assert module.slugify("AI Market Research")=="ai-market-research"
def test_slugify_chinese():assert module.slugify("AI 短剧 行业")=="ai-短剧-行业"
def test_budget_profiles_exist_and_question_limits_align():
    b=module.load_budgets();assert b["standard"]["max_workers"]<=5;assert b["deep"]["max_questions"]==8
def init(module,tmp_path):
    module.WORKSPACE_ROOT=tmp_path;args=type("A",(),{"title":"主题","slug":"topic","budget":"lite","force":False,"install_agent":False})();module.cmd_init(args);return tmp_path/"topic"
def test_init_creates_topic_expert_workspace(monkeypatch,tmp_path):
    root=init(module,tmp_path);state=json.loads((root/"state.json").read_text(encoding="utf-8"));assert state["workspace_format_version"]==2;assert not state["baseline_completed"];assert state["research_generation"]==0;assert (root/"AGENTS.md").exists();assert not (root/"AGENT.md").exists();assert (root/"context.md").exists();assert (root/"memory/lessons.jsonl").exists();monkeypatch.chdir(root);assert module.topic_dir()==root.resolve()
def test_plan_uses_one_canonical_design(tmp_path):
    root=init(module,tmp_path);args=type("A",(),{"slug":"topic","questions":3})();module.cmd_plan(args);design=json.loads((root/"plans/current-design.json").read_text(encoding="utf-8"));state=json.loads((root/"state.json").read_text(encoding="utf-8"));assert len(design["questions"])==3;assert state["open_questions"]==["q-001","q-002","q-003"];assert "q-003" in (root/"questions.md").read_text(encoding="utf-8")
