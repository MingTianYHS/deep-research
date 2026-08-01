from __future__ import annotations

import math
import tomllib
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


def load_policy(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def freshness_score(source_type: str, published_at: str | None, policy: dict[str, Any], as_of: date) -> float:
    published = parse_date(published_at)
    if not published:
        return 0.35
    age = max(0, (as_of - published).days)
    half_lives = policy["freshness_half_life_days"]
    half_life = float(half_lives.get(source_type, half_lives["default"]))
    return max(0.0, min(1.0, math.pow(0.5, age / max(1.0, half_life))))


def evaluate(cards: list[dict[str, Any]], policy: dict[str, Any], as_of: date | None = None) -> dict[str, Any]:
    as_of = as_of or datetime.now(timezone.utc).date()
    groups = Counter(card.get("independence_group") or card.get("source", {}).get("publisher") or card["id"] for card in cards)
    weights, authority_defaults = policy["weights"], policy["authority"]
    details = []
    for card in cards:
        source = card.get("source") or {}
        source_type = source.get("source_type", "unknown")
        declared = card.get("quality") or {}
        group = card.get("independence_group") or source.get("publisher") or card["id"]
        dimensions = {
            "authority": float(declared.get("authority", authority_defaults.get(source_type, authority_defaults["unknown"]))),
            "directness": float(declared.get("directness", 0.6 if card.get("quote") else 0.4)),
            "independence": 1.0 / groups[group],
            "specificity": float(declared.get("specificity", 0.7 if card.get("locator") else 0.45)),
            "freshness": freshness_score(source_type, source.get("published_at"), policy, as_of),
        }
        composite = sum(dimensions[key] * float(weights[key]) for key in weights)
        details.append({"evidence_id": card["id"], "question_id": card.get("question_id"), "source_type": source_type, "dimensions": dimensions, "score": round(composite, 4)})
    primary = {"official", "paper", "policy", "financial"}
    question_ids = {card.get("question_id") for card in cards if card.get("question_id")}
    high_risk = [card["id"] for card in cards if card.get("prompt_injection_risk") == "high"]
    return {
        "card_count": len(cards),
        "average_score": round(mean(item["score"] for item in details), 4) if details else 0.0,
        "primary_source_ratio": round(sum(1 for item in details if item["source_type"] in primary) / len(details), 4) if details else 0.0,
        "average_freshness": round(mean(item["dimensions"]["freshness"] for item in details), 4) if details else 0.0,
        "independence_groups": len(groups),
        "questions_covered": len(question_ids),
        "contradiction_cards": sum(1 for card in cards if card.get("stance") == "contradict"),
        "high_risk_cards": high_risk,
        "details": details,
    }
