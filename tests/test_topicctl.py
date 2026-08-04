import argparse
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
SPEC = importlib.util.spec_from_file_location("topicctl", SCRIPT_DIR / "topicctl.py")
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


def make_topic(root: Path, directory: str, title: str) -> Path:
    topic = root / directory
    (topic / "reports").mkdir(parents=True)
    (topic / "topic.toml").write_text(f'title="{title}"\n', encoding="utf-8")
    return topic


def test_chinese_topic_uses_chinese_directory_by_default(monkeypatch, tmp_path):
    module.researchctl.WORKSPACE_ROOT = tmp_path
    captured = {}
    monkeypatch.setattr(module.researchctl, "cmd_init", lambda args: captured.update(vars(args)))
    module.cmd_init(
        argparse.Namespace(
            title="首次线下约会准备与注意事项",
            directory_name=None,
            budget="lite",
            force=False,
            allow_language_mismatch=False,
        )
    )
    assert captured["slug"] == "首次线下约会准备与注意事项"


def test_chinese_topic_rejects_silent_english_directory(monkeypatch):
    monkeypatch.setattr(
        module.researchctl, "cmd_init", lambda args: pytest.fail("must not initialize")
    )
    with pytest.raises(SystemExit, match="Chinese topic titles"):
        module.cmd_init(
            argparse.Namespace(
                title="首次线下约会准备与注意事项",
                directory_name="first-date-prep",
                budget="lite",
                force=False,
                allow_language_mismatch=False,
            )
        )


def test_external_report_output_is_rejected(monkeypatch, tmp_path):
    topic = make_topic(
        tmp_path, "首次线下约会准备与注意事项", "首次线下约会准备与注意事项"
    )
    module.researchctl.WORKSPACE_ROOT = tmp_path
    monkeypatch.setattr(
        module.researchctl,
        "cmd_report_init",
        lambda args: pytest.fail("must not create report"),
    )
    with pytest.raises(SystemExit, match="reports directory"):
        module.cmd_report(
            argparse.Namespace(
                topic=topic.name,
                type="initial",
                title=None,
                output=str(tmp_path / "reports" / "first-date-prep.md"),
                allow_language_mismatch=False,
            )
        )


def test_report_output_at_topic_root_is_rejected(monkeypatch, tmp_path):
    topic = make_topic(tmp_path, "中文主题", "中文主题")
    module.researchctl.WORKSPACE_ROOT = tmp_path
    monkeypatch.setattr(
        module.researchctl,
        "cmd_report_init",
        lambda args: pytest.fail("must not create report"),
    )
    with pytest.raises(SystemExit, match="reports directory"):
        module.cmd_report(
            argparse.Namespace(
                topic=topic.name,
                type="final",
                title=None,
                output=str(topic / "报告.md"),
                allow_language_mismatch=False,
            )
        )


def test_report_output_inside_reports_is_allowed(monkeypatch, tmp_path):
    topic = make_topic(tmp_path, "中文主题", "中文主题")
    module.researchctl.WORKSPACE_ROOT = tmp_path
    captured = {}
    monkeypatch.setattr(
        module.researchctl, "cmd_report_init", lambda args: captured.update(vars(args))
    )
    output = topic / "reports" / "报告.md"
    module.cmd_report(
        argparse.Namespace(
            topic=topic.name,
            type="final",
            title=None,
            output=str(output),
            allow_language_mismatch=False,
        )
    )
    assert captured["output"] == str(output)


def test_explicit_language_mismatch_can_continue_to_report(monkeypatch, tmp_path):
    topic = make_topic(tmp_path, "first-date-prep", "首次线下约会准备与注意事项")
    module.researchctl.WORKSPACE_ROOT = tmp_path
    captured = {}
    monkeypatch.setattr(
        module.researchctl, "cmd_report_init", lambda args: captured.update(vars(args))
    )
    module.cmd_report(
        argparse.Namespace(
            topic=topic.name,
            type="initial",
            title=None,
            output=None,
            allow_language_mismatch=True,
        )
    )
    assert captured["slug"] == str(topic.resolve())


def test_naming_validation_reports_mismatch(tmp_path, capsys):
    topic = make_topic(tmp_path, "first-date-prep", "首次线下约会准备与注意事项")
    module.researchctl.WORKSPACE_ROOT = tmp_path
    with pytest.raises(SystemExit):
        module.cmd_validate(
            argparse.Namespace(topic=topic.name, allow_language_mismatch=False)
        )
    result = json.loads(capsys.readouterr().out)
    assert not result["valid"]
