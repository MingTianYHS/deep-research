from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .io_utils import append_jsonl, iter_jsonl, utc_now

ALLOWED_STANCES = {"support", "contradict", "context"}
TRACKING_PREFIXES = ("utm_", "ga_")
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"invalid source URL: {url}")
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_KEYS and not key.lower().startswith(TRACKING_PREFIXES)
    ]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def evidence_key(card: dict[str, Any]) -> str:
    source = card.get("source") or {}
    url = source.get("canonical_url") or source.get("url") or ""
    statement = " ".join(str(card.get("statement", "")).lower().split())
    return hashlib.sha256(f"{url}\n{statement}".encode()).hexdigest()


def normalize_card(card: dict[str, Any], question_id: str) -> dict[str, Any]:
    normalized = deepcopy(card)
    normalized.setdefault("question_id", question_id)
    normalized.setdefault("id", f"ev-{hashlib.sha256(evidence_key(normalized).encode()).hexdigest()[:16]}")
    source = normalized.setdefault("source", {})
    source["canonical_url"] = canonical_url(source.get("canonical_url") or source.get("url", ""))
    source.setdefault("accessed_at", utc_now())
    normalized.setdefault("ingested_at", utc_now())
    normalized.setdefault("prompt_injection_risk", "low")
    validate_card(normalized)
    return normalized


def validate_card(card: dict[str, Any]) -> None:
    for field in ("id", "question_id", "source", "statement", "stance"):
        if not card.get(field):
            raise ValueError(f"evidence missing {field}")
    if not isinstance(card["source"], dict) or not card["source"].get("url"):
        raise ValueError("evidence missing source.url")
    if card["stance"] not in ALLOWED_STANCES:
        raise ValueError(f"invalid evidence stance: {card['stance']}")
    confidence = float(card.get("confidence", 0.0))
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("evidence confidence must be between 0 and 1")


def ingest_worker_result(cards_path: Path, result: dict[str, Any], max_new: int) -> dict[str, Any]:
    question_id = result.get("question_id")
    cards = result.get("evidence_cards")
    if not question_id or not isinstance(cards, list):
        raise ValueError("worker result requires question_id and evidence_cards[]")
    existing_ids, existing_keys = set(), set()
    for _, card in iter_jsonl(cards_path):
        existing_ids.add(card.get("id"))
        existing_keys.add(evidence_key(card))
    accepted, duplicate_ids = [], []
    for raw in cards:
        card = normalize_card(raw, question_id)
        key = evidence_key(card)
        if card["id"] in existing_ids or key in existing_keys:
            duplicate_ids.append(card["id"])
            continue
        existing_ids.add(card["id"])
        existing_keys.add(key)
        accepted.append(card)
    if len(accepted) > max_new:
        raise ValueError(f"worker result adds {len(accepted)} cards but budget allows {max_new}")
    append_jsonl(cards_path, accepted)
    return {"accepted": len(accepted), "duplicates": len(duplicate_ids), "duplicate_ids": duplicate_ids}
