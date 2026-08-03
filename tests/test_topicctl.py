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


def test_chinese_topic_uses_chinese_directory_by_default(monkeypatch, tmp_path):
    module.researchctl.WORKSPACE_ROOT = tmp_path
    captured = {}
    monkeypatch.setattr(module.researchctl, "cmd_init", lambda args: captured.update(vars(args)))
    module.cmd_init(argparse.Namespace(title="首次线下约会准备与注意事项", directory_name=None, budget="lite", force=False, allow_language_mismatch=False))
    assert captured["slug"] == "首次线下约会准备与注意事项"


def test_chinese_topic_rejects_silent_english_directory(monkeypatch):
    monkeypatch.setattr(module.researchctl, "cmd_init", lambda args: pytest.fail("must not initialize"))
    with pytest.raises(SystemExit, match="Chinese topic titles"):
        module.cmd_init(argparse.Namespace(title="首次线下约会准备与注意事项", directory_name="first-date-prep", budget="lite", force=False, allow_language_mismatch=False))


def test_external_report_output_is_rejected(monkeypatch, tmp_path):
    root = tmp_path / "首次线下约会准备与注意事项"
    root.mkdir()
    (root / "topic.toml").write_text('title="首次线下约会准备与注意事项"\n', encoding="utf-8")
    module.researchctl.WORKSPACE_ROOT = tmp_path
    monkeypatch.setattr(module.researchctl, "cmd_report_init", lambda args: pytest.fail("must not create report"))
    with pytest.raises(SystemExit, match="must stay inside"):
        module.cmd_report(argparse.Namespace(topic=root.name, type="initial", title=None, output=str(tmp_path / "reports" / "first-date-prep.md")))


def test_naming_validation_reports_mismatch(tmp_path, capsys):
    root = tmp_path / "first-date-prep"
    root.mkdir()
    (root / "topic.toml").write_text('title="首次线下约会准备与注意事项"\n', encoding="utf-8")
    module.researchctl.WORKSPACE_ROOT = tmp_path
    with pytest.raises(SystemExit):
        module.cmd_validate(argparse.Namespace(topic=root.name, allow_language_mismatch=False))
    result = json.loads(capsys.readouterr().out)
    assert not result["valid"]
