import json
import sys
from pathlib import Path

SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts";sys.path.insert(0,str(SCRIPT_DIR))
from lib.io_utils import append_jsonl,atomic_write_json
from lib.lifecycle import record_critic_review,validate_critic_review,validate_reflection_link


def review():
    return {"review_id":"critic-1","run_id":"run-1","status":"complete","findings":[],"targeted_searches":[],"unresolved":[],"lesson_decisions":[{"candidate_id":"lesson-1","decision":"accept","reason":"reusable","type":"source_strategy","scope":"official docs","lesson":"Prefer version-pinned official sources."}],"completion_recommendation":"complete","stop_reason":"review_complete"}


def test_critic_review_is_persisted_and_reflection_must_match(tmp_path):
    root=tmp_path/"topic";(root/"logs").mkdir(parents=True);append_jsonl(root/"logs/runs.jsonl",[{"id":"run-1","status":"running"}])
    result=record_critic_review(root,review());assert not result["already_recorded"]
    reflection={"run_id":"run-1","critic_review_id":"critic-1","lesson_candidates":[{"candidate_id":"lesson-1","type":"source_strategy","scope":"official docs","lesson":"Prefer version-pinned official sources."}]}
    assert validate_reflection_link(root,reflection)["review_id"]=="critic-1"
    reflection["lesson_candidates"][0]["lesson"]="changed"
    try:validate_reflection_link(root,reflection);assert False
    except ValueError as exc:assert "does not match" in str(exc)


def test_critic_review_requires_completion_recommendation():
    value=review();value.pop("completion_recommendation");assert not validate_critic_review(value)["valid"]
