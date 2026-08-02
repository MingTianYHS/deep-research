from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from .source_attempts import normalize_url

COVERAGE = {"sufficient", "partial", "insufficient"}
STATUS = {"complete", "partial", "failed"}
PROMPT_RISK = {"low", "medium", "high", "unknown"}
VERSION_COMPATIBILITY = {"exact", "compatible", "mismatch", "not_applicable", "unknown"}
REQUIRED_LISTS = ("queries_run", "source_clusters", "source_attempts", "evidence_cards", "rejected_sources", "contradictions", "gaps", "suggested_followups")
USAGE_LIMITS = {"tool_calls": "max_tool_calls", "search_queries": "max_search_queries", "source_pages": "max_source_pages", "duration_minutes": "max_duration_minutes"}
TOKEN_USAGE = ("estimated_input_tokens", "estimated_output_tokens")
BUDGETS_FILE = Path(__file__).resolve().parents[2] / "config" / "budgets.toml"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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


def _validate_attempts(result: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    attempts: dict[str, dict[str, Any]] = {}
    values = result.get("source_attempts", []) if isinstance(result.get("source_attempts"), list) else []
    for index, attempt in enumerate(values, 1):
        if not isinstance(attempt, dict):
            errors.append(f"source_attempts[{index}] must be an object")
            continue
        attempt_id = attempt.get("id")
        if not attempt_id or attempt_id in attempts:
            errors.append(f"source_attempts[{index}] requires a unique id")
            continue
        for field in ("url", "normalized_url", "status", "tool", "access_mode"):
            if not attempt.get(field):
                errors.append(f"source_attempts[{index}] missing {field}")
        try:
            expected_url = normalize_url(str(attempt.get("url", "")))
            if attempt.get("normalized_url") != expected_url:
                errors.append(f"source_attempts[{index}] normalized_url does not match url")
        except ValueError as exc:
            errors.append(f"source_attempts[{index}] {exc}")
        if attempt.get("status") not in {"accepted", "unavailable", "rejected"}:
            errors.append(f"source_attempts[{index}] invalid status")
        eligible = attempt.get("eligible_for_evidence")
        if not isinstance(eligible, bool):
            errors.append(f"source_attempts[{index}] eligible_for_evidence must be boolean")
        if attempt.get("status") == "accepted":
            if eligible is not True:
                errors.append(f"source_attempts[{index}] accepted source must be eligible")
            if not SHA256_RE.fullmatch(str(attempt.get("content_sha256", ""))):
                errors.append(f"source_attempts[{index}] accepted source requires a SHA-256 content hash")
        if attempt.get("status") != "accepted" and eligible is True:
            errors.append(f"source_attempts[{index}] unavailable/rejected source cannot be eligible")
        attempts[str(attempt_id)] = attempt
    return attempts


def _validate_cards(result: dict[str, Any], attempts: dict[str, dict[str, Any]], errors: list[str]) -> None:
    values = result.get("evidence_cards", []) if isinstance(result.get("evidence_cards"), list) else []
    for index, card in enumerate(values, 1):
        if not isinstance(card, dict):
            errors.append(f"evidence_cards[{index}] must be an object")
            continue
        for field in ("statement", "stance", "confidence", "independence_group", "source_attempt_id", "prompt_injection_risk", "version_compatibility"):
            if field not in card or card.get(field) in (None, ""):
                errors.append(f"evidence_cards[{index}] missing {field}")
        source = card.get("source")
        if not isinstance(source, dict):
            errors.append(f"evidence_cards[{index}].source must be an object")
        else:
            for field in ("url", "title", "publisher", "source_type"):
                if not source.get(field):
                    errors.append(f"evidence_cards[{index}].source missing {field}")
        if not card.get("quote") and not card.get("locator"):
            errors.append(f"evidence_cards[{index}] requires quote or locator")
        if card.get("prompt_injection_risk") not in PROMPT_RISK:
            errors.append(f"evidence_cards[{index}] invalid prompt_injection_risk")
        if card.get("version_compatibility") not in VERSION_COMPATIBILITY:
            errors.append(f"evidence_cards[{index}] invalid version_compatibility")
        attempt = attempts.get(str(card.get("source_attempt_id")))
        if not attempt:
            errors.append(f"evidence_cards[{index}] references unknown source_attempt_id")
            continue
        if attempt.get("status") != "accepted" or not attempt.get("eligible_for_evidence"):
            errors.append(f"evidence_cards[{index}] source attempt is not accepted")
            continue
        if isinstance(source, dict) and source.get("url"):
            try:
                if normalize_url(str(source["url"])) != attempt.get("normalized_url"):
                    errors.append(f"evidence_cards[{index}] source URL does not match source attempt")
            except ValueError as exc:
                errors.append(f"evidence_cards[{index}] {exc}")
        declared_hash = card.get("content_sha256")
        if declared_hash and declared_hash != attempt.get("content_sha256"):
            errors.append(f"evidence_cards[{index}] content_sha256 does not match source attempt")
        source_version = card.get("source_version")
        if source_version and attempt.get("source_version") and source_version != attempt.get("source_version"):
            errors.append(f"evidence_cards[{index}] source_version does not match source attempt")


def validate_worker_result(result: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for key in ("run_id", "status", "question_id", "overlap_key", "coverage_status", "budget_profile", "budget_used", "stop_reason"):
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
    attempts = _validate_attempts(result, errors)
    _validate_cards(result, attempts, errors)
    usage = result.get("budget_used")
    if not isinstance(usage, dict):
        errors.append("budget_used must be an object")
    else:
        for usage_key, limit_key in USAGE_LIMITS.items():
            value = usage.get(usage_key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                errors.append(f"budget_used.{usage_key} must be non-negative")
                continue
            if value > limits[limit_key]:
                errors.append(f"budget_used.{usage_key} {value} exceeds {limit_key} {limits[limit_key]}")
        for usage_key in TOKEN_USAGE:
            value = usage.get(usage_key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"budget_used.{usage_key} must be a non-negative integer")
        same_url = usage.get("same_url_attempts_max")
        if not isinstance(same_url, (int, float)) or isinstance(same_url, bool) or same_url < 0:
            errors.append("budget_used.same_url_attempts_max must be non-negative")
        elif same_url > limits["max_same_url_attempts"]:
            errors.append("same URL retry limit exceeded")
        reserve = usage.get("output_reserve_ratio")
        if not isinstance(reserve, (int, float)) or isinstance(reserve, bool):
            errors.append("budget_used.output_reserve_ratio is required")
        elif reserve < limits["reserve_output_ratio"]:
            errors.append("output reserve ratio was not honored")
    if result.get("status") == "complete":
        if result.get("coverage_status") != "sufficient":
            errors.append("complete worker result requires sufficient coverage")
        if not result.get("evidence_cards"):
            errors.append("complete worker result requires at least one evidence card")
    if result.get("status") == "failed" and not result.get("gaps"):
        warnings.append("failed worker result should explain at least one gap")
    if result.get("stop_reason") == "acceptance_criteria_met" and result.get("coverage_status") != "sufficient":
        errors.append("acceptance_criteria_met requires sufficient coverage")
    return {"valid": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "limits": limits, "budget_verification": "self_reported"}
