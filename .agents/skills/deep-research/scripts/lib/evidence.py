from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .io_utils import append_jsonl, atomic_write_json, iter_jsonl, utc_now
from .worker_context import validate_ingest_context
from .worker_contract import profile_limits, validate_worker_result

ALLOWED_STANCES = {"support", "contradict", "context"}
TRACKING_PREFIXES = ("utm_", "ga_")
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}


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


def ingest_worker_result(cards_path: Path, result: dict[str, Any], max_new: int) -> dict[str, Any]:
    topic_root = cards_path.parent.parent
    context_validation = validate_ingest_context(topic_root, result)
    if not context_validation["valid"]: raise ValueError("invalid worker ingestion context: " + "; ".join(context_validation["errors"]))
    profile = result.get("budget_profile")
    if not profile: raise ValueError("worker result requires budget_profile")
    validation = validate_worker_result(result, profile_limits(str(profile)))
    if not validation["valid"]: raise ValueError("invalid worker result: " + "; ".join(validation["errors"]))
    question_id = str(result["question_id"]); cards = result["evidence_cards"]
    existing_ids, existing_keys = set(), set()
    for _, card in iter_jsonl(cards_path): existing_ids.add(card.get("id")); existing_keys.add(evidence_key(card))
    accepted, duplicate_ids = [], []
    for raw in cards:
        card = normalize_card(raw, question_id); key = evidence_key(card)
        if card["id"] in existing_ids or key in existing_keys: duplicate_ids.append(card["id"]); continue
        existing_ids.add(card["id"]); existing_keys.add(key); accepted.append(card)
    if len(accepted) > max_new: raise ValueError(f"worker result adds {len(accepted)} cards but budget allows {max_new}")
    append_jsonl(topic_root / "logs/source_attempts.jsonl", result["source_attempts"])
    append_jsonl(cards_path, accepted)
    worker_path = topic_root / "logs/workers" / f"{result['worker_result_id']}.json"
    logged = deepcopy(result)
    logged["ingest_summary"] = {"accepted_evidence_ids": [card["id"] for card in accepted], "duplicate_evidence_ids": duplicate_ids, "accepted_count": len(accepted), "duplicate_count": len(duplicate_ids)}
    atomic_write_json(worker_path, logged)
    return {"accepted": len(accepted), "accepted_ids": [card["id"] for card in accepted], "duplicates": len(duplicate_ids), "duplicate_ids": duplicate_ids, "worker_validation": validation, "ingest_context_validation": context_validation, "worker_result_log": str(worker_path)}
