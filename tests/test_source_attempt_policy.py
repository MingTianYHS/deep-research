import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.lean_workflow import _needs_new_search
from lib.source_attempts import may_attempt


def test_accepted_source_can_be_explicitly_refreshed(tmp_path):
    path = tmp_path / "attempts.jsonl"
    path.write_text(json.dumps({"id": "src-1", "normalized_url": "https://example.com/report", "status": "accepted"}) + "\n", encoding="utf-8")
    assert may_attempt(path, "https://example.com/report")["reason"] == "already_accepted"
    refresh = may_attempt(path, "https://example.com/report", refresh=True)
    assert refresh["allowed"] is True
    assert refresh["reason"] == "refresh_requested"
    assert refresh["reuse"]["id"] == "src-1"


def test_known_url_refresh_does_not_trigger_discovery_disconfirmation():
    assignment = {"reuse_plan": {"recommended_action": "refresh_known_sources_before_search"}}
    assert _needs_new_search(assignment) is False
    assignment["reuse_plan"]["recommended_action"] = "targeted_discovery"
    assert _needs_new_search(assignment) is True
