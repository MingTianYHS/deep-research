from pathlib import Path
import json
import sys

import pytest

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from lib.migrations import CURRENT_WORKSPACE_FORMAT, apply, inspect, plan


def workspace(tmp_path, version):
    root = tmp_path / "topic"
    (root / "evidence").mkdir(parents=True)
    (root / "topic.toml").write_text('title="x"\n', encoding="utf-8")
    (root / "state.json").write_text(json.dumps({"topic": "x", "workspace_format_version": version}), encoding="utf-8")
    (root / "evidence/cards.jsonl").write_text("", encoding="utf-8")
    (root / "claims.jsonl").write_text("", encoding="utf-8")
    return root


def test_current_workspace_requires_no_migration(tmp_path):
    root = workspace(tmp_path, CURRENT_WORKSPACE_FORMAT)
    assert inspect(root)["valid"]
    assert not plan(root)["needs_migration"]
    assert not apply(root)["applied"]


def test_older_workspace_is_rejected_instead_of_migrated(tmp_path):
    root = workspace(tmp_path, 2)
    result = inspect(root)
    assert not result["valid"]
    assert not result["needs_migration"]
    assert "create a new format-3 workspace" in result["errors"][0]
    with pytest.raises(ValueError, match="unsupported"):
        apply(root)


def test_newer_workspace_is_rejected(tmp_path):
    result = inspect(workspace(tmp_path, 99))
    assert not result["valid"]
    assert "unsupported" in result["errors"][0]
