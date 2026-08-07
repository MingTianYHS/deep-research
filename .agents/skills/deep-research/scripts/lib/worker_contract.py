from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

COVERAGE = {"sufficient", "partial", "insufficient"}
STATUS = {"complete", "partial", "failed"}
PROMPT_RISK = {"low", "medium", "high", "unknown"}
VERSION_COMPATIBILITY = {"exact", "compatible", "mismatch", "not_applicable", "unknown"}
QUERY_INTENTS = {"discovery", "primary_source", "exact_verification", "citation_backtrack", "disconfirming", "cross_language", "version_check"}
QUERY_OUTCOMES = {"candidate_found", "primary_candidate_found", "independent_candidate_found", "contradiction_found", "duplicate_only", "indirect_only", "low_yield", "quota_limited", "unavailable"}
DISCOVERY_METHODS = {"search", "known_url", "user_provided", "citation_backtrack"}
REQUIRED_LISTS = ("queries_run", "source_attempts", "evidence_cards", "gaps")
USAGE_LIMITS = {"tool_calls": "max_tool_calls", "search_queries": "max_search_queries", "source_pages": "max_source_pages"}
BUDGETS_FILE = Path(__file__).resolve().parents[2] / "config" / "budgets.toml"


def profile_limits(profile: str, budgets_file: Path | None = None) -> dict[str, Any]:
    with (budgets_file or BUDGETS_FILE).open("rb") as handle:
        profiles = tomllib.load(handle)
    if profile not in profiles:
        raise ValueError(f"unknown worker budget profile: {profile}")
    value = profiles[profile]
    return {
        "max_tool_calls": int(value["max_tool_calls_per_worker"]),
        "max_search_queries": int(value["max_search_queries_per_worker"]),
        "max_source_pages": int(value["max_source_pages_per_worker"]),
        "max_same_url_attempts": int(value["max_same_url_attempts"]),
        "max_duration_minutes": int(value["max_duration_minutes_per_worker"]),
        "reserve_output_ratio": float(value["reserve_ratio"]),
    }


def _normalized_query(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _validate_queries(result: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    queries: dict[str, dict[str, Any]] = {}
    values = result.get("queries_run", []) if isinstance(result.get("queries_run"), list) else []
    normalized: dict[str, list[dict[str, Any]]] = {}
    for index, query in enumerate(values, 1):
        if not isinstance(query, dict):
            errors.append(f"queries_run[{index}] must be an object")
            continue
        query_id = query.get("id")
        if not query_id or query_id in queries:
            errors.append(f"queries_run[{index}] requires a unique id")
            continue
        for field in ("query", "intent", "provider", "language", "outcome"):
            if not query.get(field): errors.append(f"queries_run[{index}] missing {field}")
        if "fallback_of" not in query: errors.append(f"queries_run[{index}] missing fallback_of")
        if query.get("intent") not in QUERY_INTENTS: errors.append(f"queries_run[{index}] invalid intent")
        if query.get("outcome") not in QUERY_OUTCOMES: errors.append(f"queries_run[{index}] invalid outcome")
        if query.get("intent") == "version_check" and not query.get("time_anchor"):
            errors.append(f"queries_run[{index}] version_check requires time_anchor")
        queries[str(query_id)] = query
        text = query.get("query")
        if isinstance(text, str) and text.strip(): normalized.setdefault(_normalized_query(text), []).append(query)
    for text, matches in normalized.items():
        if len({str(item.get("provider")) for item in matches}) > 1:
            errors.append(f"same query must not be broadcast to multiple providers: {text}")
    for query_id, query in queries.items():
        parent_id = query.get("fallback_of")
        if parent_id is None: continue
        parent = queries.get(str(parent_id))
        if not parent:
            errors.append(f"query {query_id} references unknown fallback_of {parent_id}")
            continue
        if str(parent_id) == query_id: errors.append(f"query {query_id} cannot fall back to itself")
        if parent.get("fallback_of") is not None: errors.append(f"query {query_id} exceeds maximum fallback depth 1")
        if _normalized_query(str(parent.get("query", ""))) == _normalized_query(str(query.get("query", ""))) and parent.get("intent") == query.get("intent"):
            errors.append(f"query {query_id} fallback must change strategy, not only provider")
    return queries


def _validate_attempts(result: dict[str, Any], queries: dict[str, dict[str, Any]], errors: list[str]) -> dict[str, dict[str, Any]]:
    attempts: dict[str, dict[str, Any]] = {}
    values = result.get("source_attempts", []) if isinstance(result.get("source_attempts"), list) else []
    for index, attempt in enumerate(values, 1):
        if not isinstance(attempt, dict):
            errors.append(f"source_attempts[{index}] must be an object"); continue
        attempt_id = attempt.get("id")
        if not attempt_id or attempt_id in attempts:
            errors.append(f"source_attempts[{index}] requires a unique id"); continue
        for field in ("url", "normalized_url", "status", "tool", "access_mode"):
            if not attempt.get(field): errors.append(f"source_attempts[{index}] missing {field}")
        if attempt.get("status") not in {"accepted", "unavailable", "rejected"}: errors.append(f"source_attempts[{index}] invalid status")
        eligible = attempt.get("eligible_for_evidence")
        if not isinstance(eligible, bool): errors.append(f"source_attempts[{index}] eligible_for_evidence must be boolean")
        if attempt.get("status") == "accepted":
            if eligible is not True: errors.append(f"source_attempts[{index}] accepted source must be eligible")
            if not attempt.get("content_sha256"): errors.append(f"source_attempts[{index}] accepted source requires content_sha256")
        if attempt.get("status") != "accepted" and eligible is True: errors.append(f"source_attempts[{index}] unavailable/rejected source cannot be eligible")
        method = attempt.get("discovery_method"); query_id = attempt.get("query_id")
        if method not in DISCOVERY_METHODS: errors.append(f"source_attempts[{index}] invalid discovery_method")
        elif method == "search":
            if not query_id or str(query_id) not in queries: errors.append(f"source_attempts[{index}] search discovery requires a valid query_id")
        elif method == "citation_backtrack":
            query = queries.get(str(query_id)) if query_id else None
            if not query or query.get("intent") != "citation_backtrack": errors.append(f"source_attempts[{index}] citation_backtrack requires a citation_backtrack query_id")
            if not attempt.get("discovered_via_source_attempt_id"): errors.append(f"source_attempts[{index}] citation_backtrack requires discovered_via_source_attempt_id")
        elif query_id is not None: errors.append(f"source_attempts[{index}] {method} discovery must not invent query_id")
        attempts[str(attempt_id)] = attempt
    for index, attempt in enumerate(values, 1):
        if not isinstance(attempt, dict) or attempt.get("discovery_method") != "citation_backtrack": continue
        parent_id = str(attempt.get("discovered_via_source_attempt_id", "")); parent = attempts.get(parent_id)
        if not parent: errors.append(f"source_attempts[{index}] references unknown discovered_via_source_attempt_id")
        elif parent.get("status") != "accepted" or not parent.get("eligible_for_evidence"): errors.append(f"source_attempts[{index}] citation parent must be an accepted Source Attempt")
        if parent_id == str(attempt.get("id")): errors.append(f"source_attempts[{index}] cannot cite itself as discovery parent")
    return attempts


def _validate_cards(result: dict[str, Any], attempts: dict[str, dict[str, Any]], errors: list[str]) -> None:
    values = result.get("evidence_cards", []) if isinstance(result.get("evidence_cards"), list) else []
    for index, card in enumerate(values, 1):
        if not isinstance(card, dict): errors.append(f"evidence_cards[{index}] must be an object"); continue
        for field in ("statement", "stance", "confidence", "independence_group", "source_attempt_id", "prompt_injection_risk", "version_compatibility"):
            if field not in card or card.get(field) in (None, ""): errors.append(f"evidence_cards[{index}] missing {field}")
        source = card.get("source")
        if not isinstance(source, dict): errors.append(f"evidence_cards[{index}].source must be an object")
        else:
            for field in ("url", "title", "publisher", "source_type"):
                if not source.get(field): errors.append(f"evidence_cards[{index}].source missing {field}")
        if not card.get("quote") and not card.get("locator"): errors.append(f"evidence_cards[{index}] requires quote or locator")
        if card.get("prompt_injection_risk") not in PROMPT_RISK: errors.append(f"evidence_cards[{index}] invalid prompt_injection_risk")
        if card.get("version_compatibility") not in VERSION_COMPATIBILITY: errors.append(f"evidence_cards[{index}] invalid version_compatibility")
        attempt = attempts.get(str(card.get("source_attempt_id")))
        if not attempt: errors.append(f"evidence_cards[{index}] references unknown source_attempt_id")
        elif attempt.get("status") != "accepted" or not attempt.get("eligible_for_evidence"): errors.append(f"evidence_cards[{index}] source attempt is not accepted")


def validate_worker_result(result: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []; warnings: list[str] = []
    if result.get("worker_result_version") != 2: errors.append("worker_result_version must be 2")
    for key in ("status", "question_id", "overlap_key", "coverage_status", "budget_profile", "budget_used", "stop_reason"):
        if key not in result or result.get(key) in (None, ""): errors.append(f"missing {key}")
    if result.get("status") not in STATUS: errors.append(f"invalid status: {result.get('status')}")
    if result.get("coverage_status") not in COVERAGE: errors.append(f"invalid coverage_status: {result.get('coverage_status')}")
    for key in REQUIRED_LISTS:
        if not isinstance(result.get(key), list): errors.append(f"{key} must be a list")
    queries = _validate_queries(result, errors); attempts = _validate_attempts(result, queries, errors); _validate_cards(result, attempts, errors)
    usage = result.get("budget_used")
    if not isinstance(usage, dict): errors.append("budget_used must be an object")
    else:
        for usage_key, limit_key in USAGE_LIMITS.items():
            value = usage.get(usage_key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0: errors.append(f"budget_used.{usage_key} must be non-negative")
            elif value > limits[limit_key]: errors.append(f"budget_used.{usage_key} {value} exceeds {limit_key} {limits[limit_key]}")
    if result.get("status") == "complete" and result.get("coverage_status") != "sufficient": errors.append("complete worker result requires sufficient coverage")
    if result.get("status") == "complete":
        if not queries: errors.append("complete version-2 worker result requires query trace")
        if result.get("budget_profile") == "deep" and not any(query.get("intent") == "disconfirming" for query in queries.values()): errors.append("complete deep worker result requires a disconfirming query")
        if not any(attempt.get("status") == "accepted" and attempt.get("eligible_for_evidence") for attempt in attempts.values()): errors.append("complete version-2 worker result requires an accepted Source Attempt")
        if not result.get("evidence_cards"): errors.append("complete version-2 worker result requires at least one Evidence Card")
    low_yield_fallback = any(query.get("fallback_of") is not None and query.get("outcome") == "low_yield" for query in queries.values())
    if low_yield_fallback:
        if result.get("status") == "complete": errors.append("second low-yield result cannot be complete")
        if result.get("stop_reason") != "low_yield_after_fallback": errors.append("second low-yield result requires stop_reason low_yield_after_fallback")
        if not result.get("gaps"): errors.append("second low-yield result requires an explicit gap")
    if result.get("status") == "failed" and not result.get("gaps"): warnings.append("failed worker result should explain at least one gap")
    if result.get("stop_reason") == "acceptance_criteria_met" and result.get("coverage_status") != "sufficient": errors.append("acceptance_criteria_met requires sufficient coverage")
    return {"valid": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "limits": limits, "budget_verification": "self_reported", "worker_result_version": 2}
