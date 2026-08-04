import argparse
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
SPEC = importlib.util.spec_from_file_location(
    "research_entrypoint", SCRIPT_DIR / "research.py"
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


def test_public_commands_are_small_and_workflow_focused():
    root = module.parser()
    subparsers = next(action for action in root._actions if action.dest == "command")
    assert set(subparsers.choices) == {
        "new",
        "plan",
        "brief",
        "start",
        "status",
        "report",
        "finish",
        "validate",
    }


def test_new_always_uses_guarded_topic_controller(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        module.topicctl, "cmd_init", lambda args: captured.update(vars(args))
    )
    module.cmd_new(
        argparse.Namespace(
            title="AI短剧市场研究",
            directory_name=None,
            budget="standard",
            allow_language_mismatch=False,
        )
    )
    assert captured["title"] == "AI短剧市场研究"
    assert captured["force"] is False


def test_report_always_uses_guarded_topic_controller(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        module.topicctl, "cmd_report", lambda args: captured.update(vars(args))
    )
    module.cmd_report(
        argparse.Namespace(
            topic=None,
            type="final",
            title=None,
            output=None,
            allow_language_mismatch=True,
        )
    )
    assert captured["allow_language_mismatch"] is True


def test_public_new_has_no_force_flag():
    parsed = module.parser().parse_args(["new", "主题"])
    assert not hasattr(parsed, "force")


def test_language_mismatch_override_is_available_for_lifecycle_commands():
    report = module.parser().parse_args(
        ["report", "topic", "--allow-language-mismatch"]
    )
    validate = module.parser().parse_args(
        ["validate", "topic", "--allow-language-mismatch"]
    )
    assert report.allow_language_mismatch is True
    assert validate.allow_language_mismatch is True


def test_public_validate_prints_one_json_result_for_naming_failure(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        module.topicctl,
        "naming_result",
        lambda topic, allow: {
            "valid": False,
            "topic": "中文主题",
            "workspace": "/tmp/english-topic",
            "errors": ["language mismatch"],
        },
    )
    with pytest.raises(SystemExit):
        module.cmd_validate(
            argparse.Namespace(topic="english-topic", allow_language_mismatch=False)
        )
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["valid"] is False
    assert result["errors"] == ["language mismatch"]
    assert output.count("{\n") == 1
