from pathlib import Path
import json
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from lib.migrations import apply, inspect, plan


def workspace(tmp_path, version="missing"):
    root = tmp_path / "topic"
    (root / "evidence").mkdir(parents=True)
    (root / "logs").mkdir()
    (root / "topic.toml").write_text('title="x"\n', encoding="utf-8")
    state = {"topic": "x", "budget_profile": "lite", "open_questions": []}
    if version != "missing":
        state["workspace_format_version"] = version
    (root / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (root / "evidence/cards.jsonl").write_text("", encoding="utf-8")
    (root / "claims.jsonl").write_text("", encoding="utf-8")
    (root / "AGENT.md").write_text("legacy instructions", encoding="utf-8")
    return root


def test_v1_workspace_migrates_to_canonical_topic_expert_v2(tmp_path):
    root = workspace(tmp_path)
    assert inspect(root)["version"] == 1
    assert plan(root)["needs_migration"]
    result = apply(root)
    assert result["applied"]
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    assert state["workspace_format_version"] == 2
    assert state["context_generated_at"]
    assert "Topic expert coordinator" in (root / "AGENTS.md").read_text(encoding="utf-8")
    assert (root / "AGENT.md").read_text(encoding="utf-8") == "legacy instructions"
    assert (root / "memory/lessons.jsonl").exists()
    assert not inspect(root)["needs_migration"]


def test_newer_workspace_is_rejected(tmp_path):
    result = inspect(workspace(tmp_path, 99))
    assert not result["valid"]
    assert "newer than runtime" in result["errors"][0]
