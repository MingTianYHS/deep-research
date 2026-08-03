from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.workspace_paths import contains_cjk, is_within, report_filename, safe_component, topic_directory_name, validate_topic_naming, workspace_root


def test_external_workspace_root(monkeypatch, tmp_path):
    target = tmp_path / "知识宇宙海" / "调研工作区"
    monkeypatch.setenv("DEEP_RESEARCH_WORKSPACE_ROOT", str(target))
    assert workspace_root(tmp_path / "repo") == target


def test_default_workspace_root(monkeypatch, tmp_path):
    monkeypatch.delenv("DEEP_RESEARCH_WORKSPACE_ROOT", raising=False)
    assert workspace_root(tmp_path) == tmp_path / "workspace" / "topics"


def test_chinese_topic_name_and_windows_safety():
    assert safe_component("中国AI市场：2026/趋势") == "中国AI市场-2026-趋势"
    assert topic_directory_name("首次线下约会准备与注意事项") == "首次线下约会准备与注意事项"
    assert contains_cjk("OpenAI Codex 配置研究")
    assert safe_component("CON") == "_CON"


def test_chinese_title_rejects_silent_english_directory():
    errors = validate_topic_naming("首次线下约会准备与注意事项", "first-date-prep")
    assert errors
    assert not validate_topic_naming("首次线下约会准备与注意事项", "first-date-prep", allow_language_mismatch=True)


def test_english_product_topic_remains_valid():
    assert not validate_topic_naming("deep-research", "deep-research")
    assert not validate_topic_naming("OpenAI Codex 配置研究", "OpenAI-Codex-配置研究")


def test_topic_artifact_path_boundary(tmp_path):
    root = tmp_path / "主题"
    assert is_within(root, root / "reports" / "报告.md")
    assert not is_within(root, tmp_path / "reports" / "报告.md")


def test_report_filename_uses_date_topic_and_type():
    now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    assert report_filename("AI短剧市场研究", "initial", now) == "20260801-AI短剧市场研究.md"
    assert report_filename("AI短剧市场研究", "update", now) == "20260801-AI短剧市场研究-更新.md"
    assert report_filename("AI短剧市场研究", "final", now) == "20260801-AI短剧市场研究-最终.md"
