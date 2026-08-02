from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .io_utils import atomic_write_json, append_jsonl, iter_jsonl, utc_now
from .worker_contract import profile_limits, validate_worker_result

ALLOWED_STANCES = {"support", "contradict", "context"}
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
TRACKING_PREFIXES = ("utm_",)


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"invalid source URL: {url}")
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in TRACKING_KEYS and not key.lower().startswith(TRACKING_PREFIXES)]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/": path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def evidence_key(card: dict[str, Any]) -> str:
    source = card.get("source") or {}; url = source.get("canonical_url") or source.get("url") or ""; statement = " ".join(str(card.get("statement", "")).lower().split())
    return hashlib.sha256(f"{url}\n{statement}".encode()).hexdigest()


def worker_result_id(result: dict[str, Any]) -> str:
    stable = deepcopy(result); stable.pop("_ingestion", None)
    return "wrk-" + hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]


def normalize_card(card: dict[str, Any], question_id: str, attempt: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(card); normalized.setdefault("question_id", question_id); source = normalized.setdefault("source", {}); source["canonical_url"] = attempt["normalized_url"]; normalized["content_sha256"] = attempt["content_sha256"]
    if attempt.get("source_version"): normalized["source_version"] = attempt["source_version"]
    normalized.setdefault("id", f"ev-{hashlib.sha256(evidence_key(normalized).encode()).hexdigest()[:16]}"); source.setdefault("accessed_at", utc_now()); normalized.setdefault("ingested_at", utc_now()); validate_card(normalized); return normalized


def validate_card(card: dict[str, Any]) -> None:
    for field in ("id", "question_id", "source", "statement", "stance", "source_attempt_id", "independence_group", "prompt_injection_risk", "version_compatibility"):
        if not card.get(field): raise ValueError(f"evidence missing {field}")
    if not isinstance(card["source"], dict) or not card["source"].get("url"): raise ValueError("evidence missing source.url")
    if card["stance"] not in ALLOWED_STANCES: raise ValueError(f"invalid evidence stance: {card['stance']}")
    confidence = float(card.get("confidence", -1.0))
    if not 0.0 <= confidence <= 1.0: raise ValueError("evidence confidence must be between 0 and 1")
    if not card.get("quote") and not card.get("locator"): raise ValueError("evidence requires quote or locator")


def _existing_worker_result(topic_root: Path, ingestion_id: str) -> dict[str, Any] | None:
    for path in (topic_root / "logs/workers").glob("*.json"):
        try: value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): continue
        if value.get("_ingestion", {}).get("id") == ingestion_id: return {"path": str(path), "value": value}
    return None


def preview_worker_result(cards_path: Path, result: dict[str, Any], max_new: int) -> dict[str, Any]:
    profile = result.get("budget_profile")
    if not profile: raise ValueError("worker result requires budget_profile")
    validation = validate_worker_result(result, profile_limits(str(profile)))
    if not validation["valid"]: raise ValueError("invalid worker result: " + "; ".join(validation["errors"]))
    topic_root = cards_path.parent.parent; ingestion_id = worker_result_id(result); previous = _existing_worker_result(topic_root, ingestion_id)
    if previous:
        return {"accepted": [], "duplicate_ids": [], "new_attempts": [], "already_ingested": True, "worker_result_id": ingestion_id, "worker_validation": validation, "worker_result_log": previous["path"], "budget_delta": previous["value"].get("_ingestion", {}).get("budget_delta", {})}
    attempts = {str(item["id"]): item for item in result["source_attempts"]}; existing_attempts = {str(item.get("id")): item for _, item in iter_jsonl(topic_root / "logs/source_attempts.jsonl") if item.get("id")}
    conflicts = sorted(key for key in set(attempts) & set(existing_attempts) if attempts[key] != existing_attempts[key])
    if conflicts: raise ValueError(f"source attempt ids already exist with different content: {conflicts}")
    new_attempts = [item for key, item in attempts.items() if key not in existing_attempts]
    existing_ids, existing_keys = set(), set()
    for _, card in iter_jsonl(cards_path): existing_ids.add(str(card.get("id"))); existing_keys.add(evidence_key(card))
    accepted, duplicate_ids = [], []
    for raw in result["evidence_cards"]:
        card = normalize_card(raw, str(result["question_id"]), attempts[str(raw["source_attempt_id"])]); key = evidence_key(card)
        if card["id"] in existing_ids or key in existing_keys: duplicate_ids.append(card["id"]); continue
        existing_ids.add(card["id"]); existing_keys.add(key); accepted.append(card)
    if len(accepted) > max_new: raise ValueError(f"worker result adds {len(accepted)} cards but budget allows {max_new}")
    usage = result["budget_used"]; delta = {"queries": int(usage["search_queries"]), "pages": int(usage["source_pages"]), "evidence_cards": len(accepted), "estimated_input_tokens": int(usage["estimated_input_tokens"]), "estimated_output_tokens": int(usage["estimated_output_tokens"])}
    return {"accepted": accepted, "duplicate_ids": duplicate_ids, "new_attempts": new_attempts, "already_ingested": False, "worker_result_id": ingestion_id, "worker_validation": validation, "worker_result_log": None, "budget_delta": delta}


def ingest_worker_result(cards_path: Path, result: dict[str, Any], max_new: int) -> dict[str, Any]:
    plan = preview_worker_result(cards_path, result, max_new)
    if plan["already_ingested"]: return {"accepted": 0, "duplicates": 0, "duplicate_ids": [], "already_ingested": True, "worker_result_id": plan["worker_result_id"], "worker_validation": plan["worker_validation"], "worker_result_log": plan["worker_result_log"], "budget_delta": plan["budget_delta"]}
    topic_root = cards_path.parent.parent; append_jsonl(topic_root / "logs/source_attempts.jsonl", plan["new_attempts"]); append_jsonl(cards_path, plan["accepted"])
    safe_question = re.sub(r"[^A-Za-z0-9_-]+", "-", str(result["question_id"])).strip("-") or "unknown"; safe_run = re.sub(r"[^A-Za-z0-9_-]+", "-", str(result["run_id"])).strip("-") or "unknown"; worker_path = topic_root / "logs/workers" / f"{safe_run}-{safe_question}-{plan['worker_result_id']}.json"
    stored = deepcopy(result); stored["_ingestion"] = {"id": plan["worker_result_id"], "ingested_at": utc_now(), "accepted_evidence": len(plan["accepted"]), "budget_delta": plan["budget_delta"]}; atomic_write_json(worker_path, stored)
    return {"accepted": len(plan["accepted"]), "duplicates": len(plan["duplicate_ids"]), "duplicate_ids": plan["duplicate_ids"], "already_ingested": False, "worker_result_id": plan["worker_result_id"], "worker_validation": plan["worker_validation"], "worker_result_log": str(worker_path), "budget_delta": plan["budget_delta"]}
