from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, exclusive_lock, read_json, utc_now

IDENTITY_ENV = (
    "DEEP_RESEARCH_COORDINATOR_ID",
    "CODEX_THREAD_ID",
    "CODEX_SESSION_ID",
)


def resolve_coordinator_id(explicit: str | None = None) -> str | None:
    if explicit and explicit.strip():
        return explicit.strip()
    for key in IDENTITY_ENV:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def acquire_or_refresh(
    root: Path,
    run_id: str,
    coordinator_id: str | None,
    *,
    lease_seconds: int = 180,
) -> dict[str, Any]:
    """Acquire or refresh one persistent coordinator lease for a topic run."""
    if not coordinator_id:
        return {
            "allowed": True,
            "enforced": False,
            "warning": (
                "No coordinator identity is available; set "
                "DEEP_RESEARCH_COORDINATOR_ID or pass --coordinator-id to enforce "
                "single-coordinator ownership."
            ),
        }
    runtime = root / ".runtime"
    lease_path = runtime / "coordinator-lease.json"
    lock_path = runtime / "coordinator-lease.lock"
    now = time.time()
    with exclusive_lock(lock_path):
        lease = read_json(lease_path, {})
        active = (
            lease.get("run_id") == run_id
            and float(lease.get("expires_at_epoch", 0)) > now
        )
        owner = str(lease.get("coordinator_id") or "")
        if active and owner and owner != coordinator_id:
            return {
                "allowed": False,
                "enforced": True,
                "owner": owner,
                "run_id": run_id,
                "expires_at_epoch": lease.get("expires_at_epoch"),
                "violation": "another coordinator holds the active topic lease",
            }
        updated = {
            "run_id": run_id,
            "coordinator_id": coordinator_id,
            "acquired_at": lease.get("acquired_at") if active else utc_now(),
            "heartbeat_at": utc_now(),
            "expires_at_epoch": now + lease_seconds,
            "lease_seconds": lease_seconds,
        }
        atomic_write_json(lease_path, updated)
        return {"allowed": True, "enforced": True, **updated}
