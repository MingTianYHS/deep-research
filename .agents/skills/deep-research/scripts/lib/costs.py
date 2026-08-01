from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from .io_utils import append_jsonl, iter_jsonl, utc_now

UNITS = {"request", "result", "page", "credit", "token", "browser_minute", "second", "other"}


def required_text(event: dict[str, Any], key: str) -> str:
    value = str(event.get(key, "")).strip()
    if not value:
        raise ValueError(f"cost event {key} must be non-empty")
    return value


def record(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    required = ("provider", "operation", "quantity", "unit", "cost_usd", "run_id")
    missing = [key for key in required if event.get(key) is None]
    if missing:
        raise ValueError(f"cost event missing: {', '.join(missing)}")
    quantity, cost = float(event["quantity"]), float(event["cost_usd"])
    if not math.isfinite(quantity) or not math.isfinite(cost):
        raise ValueError("quantity and cost_usd must be finite")
    if quantity < 0 or cost < 0:
        raise ValueError("quantity and cost_usd must be non-negative")
    if event["unit"] not in UNITS:
        raise ValueError(f"unsupported cost unit: {event['unit']}")
    normalized = {
        "provider": required_text(event, "provider"),
        "operation": required_text(event, "operation"),
        "quantity": quantity,
        "unit": event["unit"],
        "cost_usd": cost,
        "estimated": bool(event.get("estimated", False)),
        "run_id": required_text(event, "run_id"),
        "at": event.get("at") or utc_now(),
        "metadata": event.get("metadata") or {},
    }
    append_jsonl(path, [normalized])
    return normalized


def summarize(path: Path, run_id: str | None = None) -> dict[str, Any]:
    totals = defaultdict(lambda: {"cost_usd": 0.0, "events": 0, "estimated_events": 0, "quantities": defaultdict(float)})
    grand_total, event_count = 0.0, 0
    for _, event in iter_jsonl(path):
        if run_id and event.get("run_id") != run_id:
            continue
        key = f"{event['provider']}:{event['operation']}"
        bucket = totals[key]
        bucket["cost_usd"] += float(event["cost_usd"])
        bucket["events"] += 1
        bucket["estimated_events"] += int(bool(event.get("estimated")))
        bucket["quantities"][event["unit"]] += float(event["quantity"])
        grand_total += float(event["cost_usd"])
        event_count += 1
    normalized = {}
    for key, bucket in totals.items():
        normalized[key] = {"cost_usd": round(bucket["cost_usd"], 8), "events": bucket["events"], "estimated_events": bucket["estimated_events"], "quantities": {unit: value for unit, value in sorted(bucket["quantities"].items())}}
    return {"run_id": run_id, "event_count": event_count, "total_cost_usd": round(grand_total, 8), "breakdown": dict(sorted(normalized.items()))}
