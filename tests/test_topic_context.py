import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from lib.io_utils import append_jsonl, atomic_write_json
from lib.research_design import template
from lib.topic_context import apply_reflection, build_brief, resolve_topic, validate_reflection


def workspace(tmp_path, run_status="complete"):
    root = tmp_path / "topic"
    for relative in ("evidence", "memory", "plans", "logs"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "topic.toml").write_text('title="x"\n', encoding="utf-8")
    atomic_write_json(
        root / "state.json",
        {
            "topic": "x",
            "budget_profile": "lite",
            "baseline_completed": False,
            "research_generation": 0,
            "open_questions": [],
        },
    )
    for relative in ("claims.jsonl", "evidence/cards.jsonl", "memory/lessons.jsonl"):
        (root / relative).write_text("", encoding="utf-8")
    append_jsonl(
        root / "logs/runs.jsonl",
        [{"id": "run-1", "status": run_status, "finished_at": "2026-08-02T00:00:00Z"}],
    )
    return root


def reflection(**updates):
    value = {
        "run_id": "run-1",
        "summary": "baseline complete",
        "open_questions": [],
        "next_actions": ["verify changes"],
        "lesson_candidates": [
            {
                "type": "source_strategy",
                "scope": "official docs",
                "lesson": "Prefer version-pinned official sources.",
                "validated_by": "research_critic",
            }
        ],
    }
    value.update(updates)
    return value


def test_baseline_question_brief_and_current_directory_resolution(tmp_path):
    root = workspace(tmp_path)
    design = template("x", 1, "lite")
    atomic_write_json(root / "plans/current-design.json", design)
    assert build_brief(root)["mode"] == "baseline"
    question = build_brief(root, "q-001")
    assert question["mode"] == "question"
    assert question["parent_mode"] == "baseline"
    assert resolve_topic(tmp_path, None, root) == root.resolve()


def test_reflection_requires_finished_run_and_is_idempotent(tmp_path):
    root = workspace(tmp_path)
    result = apply_reflection(root, reflection())
    assert result["accepted_lessons"] == 1
    assert result["research_generation"] == 1
    assert result["baseline_completed"]
    assert build_brief(root)["mode"] == "incremental"
    with pytest.raises(ValueError, match="already reflected"):
        apply_reflection(root, reflection())


def test_partial_run_does_not_complete_baseline(tmp_path):
    root = workspace(tmp_path, "partial")
    result = apply_reflection(root, reflection())
    assert not result["baseline_completed"]


def test_reflection_requires_named_critic_validation():
    value = reflection()
    value["lesson_candidates"][0]["validated_by"] = "someone_else"
    result = validate_reflection(value)
    assert not result["valid"]
    assert any("research_critic" in error for error in result["errors"])


def test_reflection_rejects_unknown_or_unfinished_run(tmp_path):
    root = workspace(tmp_path)
    with pytest.raises(ValueError, match="finished run"):
        apply_reflection(root, reflection(run_id="run-missing"))
