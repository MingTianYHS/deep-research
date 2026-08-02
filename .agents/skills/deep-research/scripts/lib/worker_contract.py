from __future__ import annotations

from typing import Any

COVERAGE = {"sufficient", "partial", "insufficient"}
STATUS = {"complete", "partial", "failed"}
REQUIRED_LISTS = (
    "queries_run",
    "source_clusters",
    "evidence_cards",
    "rejected_sources",
    "contradictions",
    "gaps",
    "suggested_followups",
)
PROFILE_LIMITS = {
    "lite": {"max_tool_calls": 10, "max_search_queries": 4, "max_source_pages": 6, "max_same_url_attempts": 2, "max_duration_minutes": 5, "reserve_output_ratio": 0.20},
    "standard": {"max_tool_calls": 16, "max_search_queries": 6, "max_source_pages": 10, "max_same_url_attempts": 2, "max_duration_minutes": 8, "reserve_output_ratio": 0.20},
    "deep": {"max_tool_calls": 24, "max_search_queries": 10, "max_source_pages": 16, "max_same_url_attempts": 2, "max_duration_minutes": 12, "reserve_output_ratio": 0.20},
}
USAGE_LIMITS = {
    "tool_calls": "max_tool_calls",
    "search_queries": "max_search_queries",
    "source_pages": "max_source_pages",
    "duration_minutes": "max_duration_minutes",
}


def profile_limits(profile: str) -> dict[str, Any]:
    if profile not in PROFILE_LIMITS:
        raise ValueError(f"unknown worker budget profile: {profile}")
    return dict(PROFILE_LIMITS[profile])


def validate_worker_result(result: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for key in ("status", "question_id", "overlap_key", "coverage_status", "budget_used", "stop_reason"):
        if key not in result or result.get(key) in (None, ""):
            errors.append(f"missing {key}")
    if result.get("status") not in STATUS:
        errors.append(f"invalid status: {result.get('status')}")
    if result.get("coverage_status") not in COVERAGE:
        errors.append(f"invalid coverage_status: {result.get('coverage_status')}")
    for key in REQUIRED_LISTS:
        if not isinstance(result.get(key), list):
            errors.append(f"{key} must be a list")
    if isinstance(result.get("suggested_followups"), list) and len(result["suggested_followups"]) > 2:
        errors.append("suggested_followups must contain at most 2 items")

    usage = result.get("budget_used")
    if not isinstance(usage, dict):
        errors.append("budget_used must be an object")
    else:
        for usage_key, limit_key in USAGE_LIMITS.items():
            value = usage.get(usage_key)
            if not isinstance(value, (int, float)) or value < 0:
                errors.append(f"budget_used.{usage_key} must be non-negative")
                continue
            if value > limits[limit_key]:
                errors.append(f"budget_used.{usage_key} {value} exceeds {limit_key} {limits[limit_key]}")
        if usage.get("same_url_attempts_max", 0) > limits["max_same_url_attempts"]:
            errors.append("same URL retry limit exceeded")

    if result.get("status") == "complete" and result.get("coverage_status") != "sufficient":
        errors.append("complete worker result requires sufficient coverage")
    if result.get("status") == "failed" and not result.get("gaps"):
        warnings.append("failed worker result should explain at least one gap")
    if result.get("stop_reason") == "acceptance_criteria_met" and result.get("coverage_status") != "sufficient":
        errors.append("acceptance_criteria_met requires sufficient coverage")

    return {"valid": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "limits": limits}
