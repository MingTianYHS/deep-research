from __future__ import annotations

from copy import deepcopy
from typing import Any

USAGE_TO_LIMIT = {
    "queries": "max_queries",
    "pages": "max_pages",
    "evidence_cards": "max_evidence_cards",
}


class BudgetExceeded(ValueError):
    pass


def report(state: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    usage = state.get("usage", {})
    remaining = {
        key: max(0, int(profile[limit]) - int(usage.get(key, 0)))
        for key, limit in USAGE_TO_LIMIT.items()
    }
    ratios = {
        key: remaining[key] / max(1, int(profile[limit]))
        for key, limit in USAGE_TO_LIMIT.items()
    }
    return {
        "limits": {limit: profile[limit] for limit in USAGE_TO_LIMIT.values()},
        "usage": {key: int(usage.get(key, 0)) for key in USAGE_TO_LIMIT},
        "remaining": remaining,
        "remaining_ratio": min(ratios.values()),
    }


def apply_delta(
    state: dict[str, Any], profile: dict[str, Any], delta: dict[str, int], *, force: bool = False
) -> dict[str, Any]:
    updated = deepcopy(state)
    usage = updated.setdefault("usage", {})
    violations: list[str] = []
    for key, amount in delta.items():
        if key not in USAGE_TO_LIMIT:
            raise ValueError(f"unknown usage field: {key}")
        if amount < 0:
            raise ValueError(f"usage delta must be non-negative: {key}")
        projected = int(usage.get(key, 0)) + amount
        limit = int(profile[USAGE_TO_LIMIT[key]])
        if projected > limit:
            violations.append(f"{key}: projected {projected} > limit {limit}")
        usage[key] = projected
    if violations and not force:
        raise BudgetExceeded("; ".join(violations))
    return updated
