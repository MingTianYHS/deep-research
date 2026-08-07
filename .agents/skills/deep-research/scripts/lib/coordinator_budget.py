from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, exclusive_lock, read_json, utc_now


def load_limits(path: Path, profile: str) -> dict[str, int]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    selected = config.get(profile)
    if not isinstance(selected, dict):
        raise ValueError(f"unknown orchestration profile: {profile}")
    return {key: int(value) for key, value in selected.items()}


def consume_next_call(
    root: Path,
    run_id: str,
    profile: str,
    phase: str,
    next_action: str,
    config_path: Path,
) -> dict[str, Any]:
    """Atomically consume one coordinator state-machine step.

    This is a hard proxy budget for coordinator model/tool loops. It cannot see
    host billing directly, but every supported lifecycle iteration must pass
    through `research.py next`, making runaway orchestration bounded.
    """
    limits = load_limits(config_path, profile)
    runtime = root / ".runtime"
    state_path = runtime / "coordinator-budget.json"
    lock_path = runtime / "coordinator-budget.lock"
    action_key = f"{phase}:{next_action}"
    with exclusive_lock(lock_path):
        state = read_json(state_path, {})
        if state.get("run_id") != run_id:
            state = {
                "run_id": run_id,
                "profile": profile,
                "next_calls": 0,
                "action_counts": {},
                "started_at": utc_now(),
            }
        projected_calls = int(state.get("next_calls", 0)) + 1
        counts = dict(state.get("action_counts") or {})
        projected_action = int(counts.get(action_key, 0)) + 1
        violations: list[str] = []
        if projected_calls > limits["max_next_calls_per_run"]:
            violations.append(
                f"next calls {projected_calls} exceed {limits['max_next_calls_per_run']}"
            )
        if projected_action > limits["max_same_action_repeats"]:
            violations.append(
                f"action {action_key} repeated {projected_action} times; "
                f"limit is {limits['max_same_action_repeats']}"
            )
        if violations:
            state["last_blocked_at"] = utc_now()
            state["last_violations"] = violations
            atomic_write_json(state_path, state)
            return {
                "allowed": False,
                "violations": violations,
                "usage": {
                    "next_calls": int(state.get("next_calls", 0)),
                    "same_action_repeats": int(counts.get(action_key, 0)),
                },
                "limits": limits,
            }
        counts[action_key] = projected_action
        state.update(
            profile=profile,
            next_calls=projected_calls,
            action_counts=counts,
            last_phase=phase,
            last_next_action=next_action,
            updated_at=utc_now(),
        )
        atomic_write_json(state_path, state)
        return {
            "allowed": True,
            "violations": [],
            "usage": {
                "next_calls": projected_calls,
                "same_action_repeats": projected_action,
            },
            "limits": limits,
        }
