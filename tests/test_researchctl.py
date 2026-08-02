import importlib.util,json
from pathlib import Path
SCRIPT=Path(__file__).parents[1]/".agents/skills/deep-research/scripts/researchctl.py";spec=importlib.util.spec_from_file_location("researchctl",SCRIPT);module=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(module)
def test_slugify_ascii():assert module.slugify("AI Market Research")=="ai-market-research"
def test_slugify_chinese():assert module.slugify("AI 短剧 行业")=="ai-短剧-行业"
def test_budget_profiles_exist_and_question_limits_align():
    b=module.load_budgets();assert b["standard"]["max_workers"]<=5;assert b["deep"]["max_questions"]==8
def test_init_stamps_workspace_version(monkeypatch,tmp_path):
    monkeypatch.setattr(module,"WORKSPACE_ROOT",tmp_path);args=type("A",(),{"title":"主题","slug":"topic","budget":"lite","force":False,"install_agent":False})();module.cmd_init(args);state=json.loads((tmp_path/"topic/state.json").read_text());assert state["workspace_format_version"]==1;assert (tmp_path/"topic/logs/source_attempts.jsonl").exists()
