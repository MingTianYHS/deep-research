from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.workspace_paths import report_filename, safe_component, workspace_root


def test_external_workspace_root(monkeypatch, tmp_path):
    target = tmp_path / "知识宇宙海" / "调研工作区"
    monkeypatch.setenv("DEEP_RESEARCH_WORKSPACE_ROOT", str(target))
    assert workspace_root(tmp_path / "repo") == target


def test_default_workspace_root(monkeypatch, tmp_path):
    monkeypatch.delenv("DEEP_RESEARCH_WORKSPACE_ROOT", raising=False)
    assert workspace_root(tmp_path) == tmp_path / "workspace" / "topics"


def test_chinese_topic_name_and_windows_safety():
    assert safe_component("中国AI市场：2026/趋势") == "中国AI市场-2026-趋势"
    assert safe_component("CON") == "_CON"


def test_report_filename_uses_date_topic_and_type():
    now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    assert report_filename("AI短剧市场研究", "initial", now) == "20260801-AI短剧市场研究.md"
    assert report_filename("AI短剧市场研究", "update", now) == "20260801-AI短剧市场研究-更新.md"
    assert report_filename("AI短剧市场研究", "final", now) == "20260801-AI短剧市场研究-最终.md"
