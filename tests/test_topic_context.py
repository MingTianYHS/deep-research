import json,sys
from pathlib import Path
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts";sys.path.insert(0,str(SCRIPT_DIR))
from lib.topic_context import apply_reflection,build_brief,resolve_topic,validate_reflection

def workspace(tmp_path):
    root=tmp_path/"topic";(root/"evidence").mkdir(parents=True);(root/"memory").mkdir();(root/"plans").mkdir();(root/"logs").mkdir();(root/"topic.toml").write_text('title="x"\n',encoding="utf-8");(root/"state.json").write_text(json.dumps({"topic":"x","budget_profile":"lite","baseline_completed":False,"research_generation":0,"open_questions":[]}),encoding="utf-8");(root/"claims.jsonl").write_text("");(root/"evidence/cards.jsonl").write_text("");(root/"memory/lessons.jsonl").write_text("");return root

def test_baseline_brief_and_current_directory_resolution(tmp_path):
    root=workspace(tmp_path);assert build_brief(root)["mode"]=="baseline";assert resolve_topic(tmp_path,None,root)==root.resolve()
def test_reflection_creates_validated_lesson_and_generation(tmp_path):
    root=workspace(tmp_path);value={"run_id":"run-1","summary":"baseline complete","open_questions":["q-2"],"next_actions":["verify q-2"],"lesson_candidates":[{"type":"source_strategy","scope":"official docs","lesson":"Prefer version-pinned official sources.","validated_by":"research_critic"}]};result=apply_reflection(root,value);assert result["accepted_lessons"]==1;assert result["research_generation"]==1;assert build_brief(root)["mode"]=="incremental";assert (root/"context.md").exists()
def test_reflection_requires_critic_validation():
    value={"run_id":"r","summary":"x","open_questions":[],"next_actions":[],"lesson_candidates":[{"type":"source_strategy","lesson":"x"}]};assert not validate_reflection(value)["valid"]
