from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

FAILURE = re.compile(r"Exit code:\s*(?:1|2|124)\b|403\s*:\s*Forbidden|404\s*:\s*Not Found|Method not found|timed out|browser is already running|CRAWL_LIVECRAWL_TIMEOUT", re.I)
URL = re.compile(r"https?://[^\s\\\"']+")


def _load(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL line {number}: {exc}") from exc
    return rows


def audit_rollout(path: Path, *, max_tool_calls: int = 24, max_failed_calls: int = 3) -> dict[str, Any]:
    rows = _load(path)
    meta = next((row.get("payload", {}) for row in rows if row.get("type") == "session_meta"), {})
    source = meta.get("source", {}).get("subagent", {})
    guardian = source.get("other") == "guardian"
    spawn = source.get("thread_spawn", {}) if isinstance(source, dict) else {}
    agent_path = spawn.get("agent_path")
    agent_role = spawn.get("agent_role")
    calls: list[dict[str, Any]] = []
    outputs: dict[str, str] = {}
    assistant_final = False
    context_compactions = 0
    guardian_turns = 0
    task_complete_message = None
    final_tokens: dict[str, Any] = {}
    for row in rows:
        payload = row.get("payload", {})
        if row.get("type") == "response_item" and payload.get("type") == "function_call":
            calls.append(payload)
        elif row.get("type") == "response_item" and payload.get("type") == "function_call_output":
            outputs[payload.get("call_id", "")] = str(payload.get("output", ""))
        elif row.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "assistant":
            if payload.get("phase") not in {"commentary", "analysis"}:
                assistant_final = True
        elif row.get("type") == "event_msg":
            event_type = payload.get("type")
            if event_type == "context_compacted": context_compactions += 1
            elif event_type == "task_started" and guardian: guardian_turns += 1
            elif event_type == "task_complete": task_complete_message = payload.get("last_agent_message")
            elif event_type == "token_count": final_tokens = payload.get("info", {}).get("total_token_usage", {})
    failed = [call for call in calls if FAILURE.search(outputs.get(call.get("call_id", ""), ""))]
    urls: list[str] = []
    for call in calls:
        urls.extend(URL.findall(str(call.get("arguments", ""))))
    normalized = [url.rstrip(";,.)") for url in urls]
    duplicates = {url: count for url, count in Counter(normalized).items() if count > 1}
    final_present = bool(task_complete_message) or assistant_final
    custom_agent = bool(agent_path or agent_role)
    gates = {"custom_agent": guardian or custom_agent, "final_message": guardian or final_present, "maximum_tool_calls": len(calls) <= max_tool_calls, "maximum_failed_calls": len(failed) <= max_failed_calls}
    return {"file": str(path), "session_kind": "guardian" if guardian else meta.get("thread_source", "unknown"), "cwd": meta.get("cwd"), "agent_nickname": meta.get("agent_nickname"), "agent_path": agent_path, "agent_role": agent_role, "custom_agent": custom_agent, "tool_calls": len(calls), "tool_names": dict(Counter(call.get("name", "unknown") for call in calls)), "failed_or_nonproductive_calls": len(failed), "duplicate_urls": duplicates, "context_compactions": context_compactions, "guardian_turns": guardian_turns, "final_message_present": final_present, "token_usage": final_tokens, "gates": gates, "passes_all_gates": all(gates.values())}
