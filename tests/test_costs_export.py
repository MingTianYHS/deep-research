from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.costs import record, summarize
from lib.package_export import export_topic, verify_package


def test_cost_ledger_normalizes_and_summarizes(tmp_path):
    path = tmp_path / "costs.jsonl"
    record(path, {"provider": "exa", "operation": "search", "quantity": 2, "unit": "request", "cost_usd": 0.014, "estimated": True, "run_id": "run-1"})
    record(path, {"provider": "exa", "operation": "search", "quantity": 3, "unit": "request", "cost_usd": 0.021, "estimated": False, "run_id": "run-1"})
    result = summarize(path, "run-1")
    assert result["event_count"] == 2
    assert result["total_cost_usd"] == 0.035
    assert result["breakdown"]["exa:search"]["quantities"]["request"] == 5


def test_export_is_reproducible_and_verifiable(tmp_path):
    topic = tmp_path / "topic"; topic.mkdir()
    (topic / "topic.toml").write_text('title = "Example"\n', encoding="utf-8")
    (topic / "state.json").write_text('{}\n', encoding="utf-8")
    (topic / "reports").mkdir(); (topic / "reports/report.md").write_text("Report\n", encoding="utf-8")
    (topic / "cache").mkdir(); (topic / "cache/ignored.txt").write_text("ignore", encoding="utf-8")
    first, second = tmp_path / "one.zip", tmp_path / "two.zip"
    result_one = export_topic(topic, first); result_two = export_topic(topic, second)
    assert result_one["archive_sha256"] == result_two["archive_sha256"]
    assert verify_package(first)["valid"]
