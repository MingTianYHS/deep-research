import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.coordinator_lease import acquire_or_refresh, resolve_coordinator_id


def test_missing_identity_is_explicitly_unenforced(tmp_path):
    result = acquire_or_refresh(tmp_path, "run-1", None)
    assert result["allowed"] is True
    assert result["enforced"] is False
    assert "coordinator identity" in result["warning"]


def test_second_coordinator_is_blocked_until_expiry(tmp_path):
    first = acquire_or_refresh(tmp_path, "run-1", "coordinator-a")
    second = acquire_or_refresh(tmp_path, "run-1", "coordinator-b")
    assert first["allowed"] is True
    assert second["allowed"] is False
    assert second["owner"] == "coordinator-a"

    path = tmp_path / ".runtime/coordinator-lease.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["expires_at_epoch"] = 0
    path.write_text(json.dumps(stored), encoding="utf-8")
    takeover = acquire_or_refresh(tmp_path, "run-1", "coordinator-b")
    assert takeover["allowed"] is True
    assert takeover["coordinator_id"] == "coordinator-b"


def test_same_coordinator_refreshes_lease(tmp_path):
    first = acquire_or_refresh(tmp_path, "run-1", "coordinator-a")
    second = acquire_or_refresh(tmp_path, "run-1", "coordinator-a")
    assert second["allowed"] is True
    assert second["acquired_at"] == first["acquired_at"]
    assert second["expires_at_epoch"] >= first["expires_at_epoch"]


def test_identity_prefers_explicit_then_environment(monkeypatch):
    monkeypatch.setenv("DEEP_RESEARCH_COORDINATOR_ID", "env-id")
    assert resolve_coordinator_id("explicit-id") == "explicit-id"
    assert resolve_coordinator_id() == "env-id"
