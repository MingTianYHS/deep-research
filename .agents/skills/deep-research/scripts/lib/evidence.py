from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .io_utils import append_jsonl, atomic_write_json, iter_jsonl, read_json, utc_now
from .source_attempts import normalize_url
from .worker_context import validate_ingest_context
from .worker_contract import profile_limits, validate_worker_result

ALLOWED_STANCES = {"support", "contradict", "context"}
TRACKING_PREFIXES = ("utm_", "ga_")
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc: raise ValueError(f"invalid source URL: {url}")
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in TRACKING_KEYS and not key.lower().startswith(TRACKING_PREFIXES)]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/": path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def evidence_key(card: dict[str, Any]) -> str:
    source = card.get("source") or {}; url = source.get("canonical_url") or source.get("url") or ""; statement = " ".join(str(card.get("statement", "")).lower().split())
    return hashlib.sha256(f"{url}\n{statement}".encode()).hexdigest()


def normalize_card(card: dict[str, Any], question_id: str) -> dict[str, Any]:
    normalized = deepcopy(card); normalized.setdefault("question_id", question_id); normalized.setdefault("id", f"ev-{hashlib.sha256(evidence_key(normalized).encode()).hexdigest()[:16]}")
    source = normalized.setdefault("source", {}); source["canonical_url"] = canonical_url(source.get("canonical_url") or source.get("url", "")); source.setdefault("accessed_at", utc_now())
    normalized.setdefault("ingested_at", utc_now()); validate_card(normalized); return normalized


def validate_card(card: dict[str, Any]) -> None:
    for field in ("id", "question_id", "source", "statement", "stance", "source_attempt_id", "independence_group", "prompt_injection_risk", "version_compatibility"):
        if not card.get(field): raise ValueError(f"evidence missing {field}")
    if not isinstance(card["source"], dict) or not card["source"].get("url"): raise ValueError("evidence missing source.url")
    if card["stance"] not in ALLOWED_STANCES: raise ValueError(f"invalid evidence stance: {card['stance']}")
    confidence = float(card.get("confidence", -1.0))
    if not 0.0 <= confidence <= 1.0: raise ValueError("evidence confidence must be between 0 and 1")
    if not card.get("quote") and not card.get("locator"): raise ValueError("evidence requires quote or locator")


def _result_digest(result: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _append_missing(path: Path, records: list[dict[str, Any]], key: str = "id") -> None:
    existing = {item.get(key) for _, item in iter_jsonl(path) if item.get(key)}
    append_jsonl(path, [item for item in records if item.get(key) not in existing])


def _validate_ingest_integrity(result: dict[str, Any]) -> None:
    errors: list[str] = []; attempts: dict[str, dict[str, Any]] = {}
    for index, attempt in enumerate(result.get("source_attempts", []), 1):
        if not isinstance(attempt, dict): continue
        attempt_id = str(attempt.get("id", "")); attempts[attempt_id] = attempt
        try: normalized = normalize_url(str(attempt.get("url", "")))
        except ValueError as exc: errors.append(f"source_attempts[{index}] invalid url: {exc}"); continue
        if attempt.get("normalized_url") != normalized: errors.append(f"source_attempts[{index}] normalized_url does not match url")
        if attempt.get("status") == "accepted" and not SHA256_RE.fullmatch(str(attempt.get("content_sha256", ""))): errors.append(f"source_attempts[{index}] content_sha256 must be 64 lowercase hexadecimal characters")
    for index, card in enumerate(result.get("evidence_cards", []), 1):
        if not isinstance(card, dict): continue
        attempt = attempts.get(str(card.get("source_attempt_id", ""))); source = card.get("source") or {}
        if not attempt or not isinstance(source, dict): continue
        try: source_url = normalize_url(str(source.get("url", "")))
        except ValueError as exc: errors.append(f"evidence_cards[{index}] invalid source.url: {exc}"); continue
        if source_url != attempt.get("normalized_url"): errors.append(f"evidence_cards[{index}] source.url does not match its Source Attempt")
    usage = result.get("budget_used") or {}; queries = result.get("queries_run", []); source_attempts = result.get("source_attempts", [])
    if usage.get("search_queries") != len(queries): errors.append("budget_used.search_queries must equal queries_run count")
    if usage.get("source_pages") != len(source_attempts): errors.append("budget_used.source_pages must equal source_attempts count")
    if errors: raise ValueError("invalid worker source integrity: " + "; ".join(sorted(set(errors))))


def _resume_pending(topic_root: Path, pending_path: Path, result: dict[str, Any], max_new: int) -> dict[str, Any]:
    pending = read_json(pending_path, {})
    if pending.get("input_sha256") != _result_digest(result): raise ValueError(f"pending worker transaction differs from retry: {result.get('worker_result_id')}")
    accepted_cards = pending.get("accepted_cards", [])
    if not isinstance(accepted_cards, list) or len(accepted_cards) > max_new: raise ValueError("pending worker transaction exceeds current Evidence budget")
    _append_missing(topic_root / "logs/source_attempts.jsonl", pending.get("source_attempts", [])); _append_missing(topic_root / "evidence/cards.jsonl", accepted_cards)
    worker_path = topic_root / "logs/workers" / f"{result['worker_result_id']}.json"; atomic_write_json(worker_path, pending["logged"]); pending_path.unlink(missing_ok=True)
    outcome = dict(pending["outcome"]); outcome["recovered_transaction"] = True; return outcome


def ingest_worker_result(cards_path: Path, result: dict[str, Any], max_new: int) -> dict[str, Any]:
    topic_root = cards_path.parent.parent; worker_id = result.get("worker_result_id"); pending_path = topic_root / "logs/workers" / f".{worker_id}.pending.json"; pending_exists = pending_path.exists()
    context_validation = validate_ingest_context(topic_root, result, allow_existing_worker=pending_exists)
    if not context_validation["valid"]: raise ValueError("invalid worker ingestion context: " + "; ".join(context_validation["errors"]))
    profile = result.get("budget_profile")
    if not profile: raise ValueError("worker result requires budget_profile")
    validation = validate_worker_result(result, profile_limits(str(profile)))
    if not validation["valid"]: raise ValueError("invalid worker result: " + "; ".join(validation["errors"]))
    _validate_ingest_integrity(result)
    if pending_exists: return _resume_pending(topic_root, pending_path, result, max_new)
    question_id = str(result["question_id"]); cards = result["evidence_cards"]; existing_ids, existing_keys = set(), set()
    for _, card in iter_jsonl(cards_path): existing_ids.add(card.get("id")); existing_keys.add(evidence_key(card))
    accepted, duplicate_ids = [], []
    for raw in cards:
        card = normalize_card(raw, question_id); key = evidence_key(card)
        if card["id"] in existing_ids or key in existing_keys: duplicate_ids.append(card["id"]); continue
        existing_ids.add(card["id"]); existing_keys.add(key); accepted.append(card)
    if len(accepted) > max_new: raise ValueError(f"worker result adds {len(accepted)} cards but budget allows {max_new}")
    worker_path = topic_root / "logs/workers" / f"{result['worker_result_id']}.json"; logged = deepcopy(result); logged["ingest_summary"] = {"accepted_evidence_ids": [card["id"] for card in accepted], "duplicate_evidence_ids": duplicate_ids, "accepted_count": len(accepted), "duplicate_count": len(duplicate_ids)}
    outcome = {"accepted": len(accepted), "accepted_ids": [card["id"] for card in accepted], "duplicates": len(duplicate_ids), "duplicate_ids": duplicate_ids, "worker_validation": validation, "ingest_context_validation": context_validation, "worker_result_log": str(worker_path)}
    atomic_write_json(pending_path, {"input_sha256": _result_digest(result), "source_attempts": result["source_attempts"], "accepted_cards": accepted, "logged": logged, "outcome": outcome})
    _append_missing(topic_root / "logs/source_attempts.jsonl", result["source_attempts"]); _append_missing(cards_path, accepted); atomic_write_json(worker_path, logged); pending_path.unlink(missing_ok=True); return outcome
