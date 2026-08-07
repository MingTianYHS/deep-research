import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import lib.lean_workflow as lean
from lib.coordinator_budget import consume_next_call


def write_state(root: Path, profile: str = "standard") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "state.json").write_text(
        json.dumps({"budget_profile": profile, "active_run_id": "run-1"}),
        encoding="utf-8",
    )


def write_limits(path: Path) -> None:
    path.write_text(
        """
[standard]
max_next_calls_per_run = 2
max_same_action_repeats = 1
max_critic_reviews = 1
max_targeted_searches = 1
""".strip(),
        encoding="utf-8",
    )


def test_coordinator_budget_blocks_repeated_action_atomically(tmp_path):
    config = tmp_path / "orchestration.toml"
    write_limits(config)
    first = consume_next_call(
        tmp_path, "run-1", "standard", "worker", "delegate", config
    )
    second = consume_next_call(
        tmp_path, "run-1", "standard", "worker", "delegate", config
    )
    assert first["allowed"] is True
    assert second["allowed"] is False
    assert second["usage"]["next_calls"] == 1


def test_coordinator_budget_resets_for_new_run(tmp_path):
    config = tmp_path / "orchestration.toml"
    write_limits(config)
    consume_next_call(tmp_path, "run-1", "standard", "worker", "delegate", config)
    fresh = consume_next_call(tmp_path, "run-2", "standard", "worker", "delegate", config)
    assert fresh["allowed"] is True
    assert fresh["usage"]["next_calls"] == 1


def test_standard_blocks_full_critic_recheck(monkeypatch, tmp_path):
    write_state(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    write_limits(config_dir / "orchestration.toml")
    monkeypatch.setattr(
        lean,
        "derive_strict_workflow",
        lambda *_args: {
            "active_run_id": "run-1",
            "phase": "critic_recheck",
            "next_action": "invoke_research_critic",
            "agent": "research_critic",
            "assignments": [{"assignment_version": 1}],
            "progress": {"previous_critic_review_id": "critic-1"},
        },
    )
    monkeypatch.setattr(lean, "reviews_for_run", lambda *_args: [{"id": "critic-1"}])
    result = lean.derive_workflow(tmp_path, tmp_path)
    assert result["phase"] == "review_budget_exhausted"
    assert result["requires_user_input"] is True
    assert result["agent"] is None
    assert result["assignments"] == []


def test_standard_caps_targeted_searches(monkeypatch, tmp_path):
    write_state(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    write_limits(config_dir / "orchestration.toml")
    monkeypatch.setattr(
        lean,
        "derive_strict_workflow",
        lambda *_args: {
            "active_run_id": "run-1",
            "phase": "critic_remediation",
            "next_action": "delegate_targeted_searches",
            "agent": "topic_researcher",
            "assignments": [{"id": "a"}, {"id": "b"}],
            "progress": {},
        },
    )
    result = lean.derive_workflow(tmp_path, tmp_path)
    assert result["assignments"] == [{"id": "a"}]
    assert result["progress"]["targeted_searches_requested"] == 2
    assert result["progress"]["targeted_searches_dispatched"] == 1
