from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .claims import materialize
from .io_utils import append_jsonl, atomic_write_json, iter_jsonl, read_json, utc_now

MAX_EVIDENCE = 8
MAX_SOURCES = 8
MAX_QUERIES = 8
MAX_CLAIMS = 8
MAX_BACKLOG = 5
MAX_MEMORY_CHARS = 8_000
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
PRIORITIES = {"high", "medium", "low"}
FRESH_DAYS = {"news": 7, "social": 3, "official": 180, "policy": 180, "financial": 90, "paper": 365, "interview": 180, "blog": 90, "unknown": 30}
DELTA_FIELDS = ("new_claims", "strengthened_claims", "weakened_claims", "new_connections", "new_hypotheses", "remaining_gaps")


def _clip(value: Any, maximum: int) -> str:
    text = " ".join(str(value or "").split()); return text if len(text) <= maximum else text[: maximum - 1].rstrip() + "…"


def _tokens(value: Any) -> set[str]:
    text = str(value or "").casefold(); result = set(re.findall(r"[a-z0-9][a-z0-9._-]+", text)); han = "".join(re.findall(r"[\u4e00-\u9fff]", text)); result.update(han[index:index + 2] for index in range(max(0, len(han) - 1))); return result


def _iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip(): return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")); return (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed).astimezone(timezone.utc)
    except ValueError: return None


def _freshness(card: dict[str, Any], now: datetime) -> str:
    source = card.get("source") or {}; checked = _iso(source.get("accessed_at") or card.get("ingested_at"))
    if checked is None: return "unknown"
    limit = FRESH_DAYS.get(str(source.get("source_type") or "unknown"), FRESH_DAYS["unknown"]); return "fresh" if (now - checked).days <= limit else "stale"


def load_backlog(root: Path) -> dict[str, Any]:
    value = read_json(root / "plans/research-backlog.json", {})
    if not isinstance(value, dict): return {"schema_version": 1, "generated_from_run": None, "items": []}
    items = value.get("items") if isinstance(value.get("items"), list) else []
    return {"schema_version": 1, "generated_from_run": value.get("generated_from_run"), "generated_at": value.get("generated_at"), "items": items[:MAX_BACKLOG]}


def validate_knowledge_delta(value: Any) -> list[str]:
    if not isinstance(value, dict): return ["knowledge_delta must be an object"]
    errors: list[str] = []
    for key in DELTA_FIELDS:
        items = value.get(key)
        if not isinstance(items, list): errors.append(f"knowledge_delta.{key} must be a list")
        elif len(items) > 8: errors.append(f"knowledge_delta.{key} allows at most 8 items")
    return errors


def validate_next_research(value: Any, known_evidence: set[str] | None = None) -> list[str]:
    if not isinstance(value, list): return ["next_research must be a list"]
    errors: list[str] = []
    if len(value) > MAX_BACKLOG: errors.append(f"next_research allows at most {MAX_BACKLOG} items")
    seen: set[str] = set()
    for index, item in enumerate(value, 1):
        if not isinstance(item, dict): errors.append(f"next_research[{index}] must be an object"); continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not SAFE_ID.fullmatch(item_id): errors.append(f"next_research[{index}].id must be a safe string")
        elif item_id in seen: errors.append(f"next_research[{index}].id is duplicated")
        else: seen.add(item_id)
        for field in ("question", "reason", "gap_type"):
            if not isinstance(item.get(field), str) or not item[field].strip(): errors.append(f"next_research[{index}].{field} must be non-empty")
        if item.get("priority") not in PRIORITIES: errors.append(f"next_research[{index}].priority must be high, medium, or low")
        criteria = item.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria: errors.append(f"next_research[{index}].acceptance_criteria must be a non-empty list")
        evidence_ids = item.get("known_evidence_ids")
        if not isinstance(evidence_ids, list): errors.append(f"next_research[{index}].known_evidence_ids must be a list")
        elif known_evidence is not None:
            unknown = sorted(set(map(str, evidence_ids)) - known_evidence)
            if unknown: errors.append(f"next_research[{index}] references unknown Evidence: {unknown}")
    return errors


def _workers(root: Path) -> list[dict[str, Any]]:
    directory = root / "logs/workers"
    if not directory.is_dir(): return []
    return [value for path in sorted(directory.glob("*.json")) if isinstance((value := read_json(path, {})), dict)]


def _select_cards(all_cards: list[dict[str, Any]], question_id: str | None, question_text: str | None) -> list[dict[str, Any]]:
    if not question_id and not question_text: return all_cards[-MAX_EVIDENCE:]
    target = _tokens(question_text); ranked: list[tuple[int, int, dict[str, Any]]] = []
    for index, card in enumerate(all_cards):
        same = card.get("question_id") == question_id; score = (4 if same else 0) + len(target & _tokens(card.get("statement")))
        if same or score > 0: ranked.append((score, index, card))
    if not ranked: return all_cards[-MAX_EVIDENCE:]
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True); return [item[2] for item in ranked[:MAX_EVIDENCE]]


def _select_queries(root: Path, question_id: str | None, question_text: str | None) -> list[dict[str, Any]]:
    target = _tokens(question_text); candidates: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []; position = 0
    for worker in _workers(root):
        for query in worker.get("queries_run", []) if isinstance(worker.get("queries_run"), list) else []:
            if not isinstance(query, dict) or not str(query.get("query") or "").strip(): continue
            same = worker.get("question_id") == question_id; score = (4 if same else 0) + len(target & _tokens(query.get("query"))); candidates.append((score, position, worker, query)); position += 1
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True); selected: list[dict[str, Any]] = []; seen: set[tuple[str, str]] = set()
    for _, _, worker, query in candidates:
        key = (" ".join(str(query["query"]).casefold().split()), str(query.get("intent") or ""))
        if key in seen: continue
        seen.add(key); selected.append({"query": _clip(query.get("query"), 300), "intent": query.get("intent"), "provider": query.get("provider"), "time_anchor": query.get("time_anchor"), "outcome": query.get("outcome"), "run_id": worker.get("run_id"), "question_id": worker.get("question_id")})
        if len(selected) >= MAX_QUERIES: break
    return selected


def build_reuse_plan(root: Path, question_id: str | None = None, question_text: str | None = None) -> dict[str, Any]:
    state = read_json(root / "state.json", {}); now = datetime.now(timezone.utc)
    attempts = {str(item.get("id")): item for _, item in iter_jsonl(root / "logs/source_attempts.jsonl") if item.get("id")}
    all_cards = [item for _, item in iter_jsonl(root / "evidence/cards.jsonl") if item.get("id")]; cards = _select_cards(all_cards, question_id, question_text); evidence_ids = {str(item["id"]) for item in cards}
    relevant_claims = []
    for claim in materialize(root / "claims.jsonl").values():
        linked = [str(item.get("evidence_id")) for item in claim.get("relations", []) if isinstance(item, dict)]
        if evidence_ids.intersection(linked): relevant_claims.append({"id": claim.get("id"), "text": _clip(claim.get("text"), 300), "status": claim.get("status"), "confidence": claim.get("confidence"), "evidence_ids": sorted(evidence_ids.intersection(linked))})
    relevant_claims = relevant_claims[-MAX_CLAIMS:]
    sources: dict[str, dict[str, Any]] = {}; evidence_summary = []; freshness_values: list[str] = []
    for card in cards:
        source = card.get("source") or {}; url = str(source.get("canonical_url") or source.get("url") or "")
        if not url: continue
        freshness = _freshness(card, now); freshness_values.append(freshness); attempt = attempts.get(str(card.get("source_attempt_id")), {})
        existing = sources.setdefault(url, {"url": url, "title": _clip(source.get("title"), 180), "publisher": _clip(source.get("publisher"), 120), "source_type": source.get("source_type"), "last_checked_at": source.get("accessed_at") or card.get("ingested_at"), "content_sha256": attempt.get("content_sha256"), "freshness": freshness, "evidence_ids": [], "covered_questions": []})
        existing["evidence_ids"].append(str(card["id"])); origin_question = str(card.get("question_id") or "")
        if origin_question and origin_question not in existing["covered_questions"]: existing["covered_questions"].append(origin_question)
        if existing["freshness"] != "stale" and freshness == "stale": existing["freshness"] = "stale"
        evidence_summary.append({"id": card.get("id"), "original_question_id": card.get("question_id"), "cross_question": bool(question_id and card.get("question_id") != question_id), "statement": _clip(card.get("statement"), 320), "stance": card.get("stance"), "confidence": card.get("confidence"), "url": url, "freshness": freshness})
    action = "targeted_discovery" if not cards else "refresh_known_sources_before_search" if {"stale", "unknown"}.intersection(freshness_values) else "reuse_existing_evidence_before_search"
    return {"research_mode": "incremental" if state.get("baseline_completed") else "baseline", "since": state.get("last_run_at"), "question_id": question_id, "recommended_action": action, "existing_evidence": evidence_summary, "relevant_claims": relevant_claims, "known_sources": list(sources.values())[-MAX_SOURCES:], "prior_queries": _select_queries(root, question_id, question_text), "next_research": load_backlog(root)["items"], "reuse_rules": ["Reuse fresh Evidence before using a search tool.", "Cross-question reuse requires an explicit relevance rationale.", "For stale or unknown sources, refresh the known URL directly before broad discovery.", "Do not repeat a prior query unless freshness, scope, version, remediation, or a previous low-yield result justifies it.", "If existing Evidence satisfies the assignment, return reused_evidence_ids and perform no search."]}


def render_current_memory(root: Path) -> dict[str, Any]:
    plan = build_reuse_plan(root); state = read_json(root / "state.json", {})
    lines = ["# 当前研究记忆", "", "> 这是从 Claim、Evidence、Source Attempt 和研究 Backlog 生成的有界视图，不是新的证据源。", "", "## 状态", "", f"- Mode: `{plan['research_mode']}`", f"- Last run: `{state.get('last_run_at')}`", f"- Knowledge status: `{state.get('knowledge_status', 'empty')}`", "", "## 已有认知", ""]
    lines += [f"- `{claim.get('id')}` [{claim.get('status')}] {claim.get('text')}" for claim in plan["relevant_claims"]] or ["- 暂无已连接的 Claim。"]
    lines += ["", "## 已知来源", ""] + ([f"- [{source.get('freshness')}] {source.get('url')} — Evidence: {', '.join(source.get('evidence_ids', []))}" for source in plan["known_sources"]] or ["- 暂无。"]) + ["", "## 后续调研", ""]
    lines += [f"- [{item.get('priority')}] `{item.get('id')}` {item.get('question')} — {item.get('reason')}" for item in plan["next_research"]] or ["- 暂无。"]
    body = "\n".join(lines).strip() + "\n"
    if len(body) > MAX_MEMORY_CHARS:
        marker = "\n\n> 研究记忆已按字符预算截断；按 ID 加载 Claim 或 Evidence。\n"; body = body[: MAX_MEMORY_CHARS - len(marker)].rstrip() + marker
    path = root / "memory/current.md"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body, encoding="utf-8")
    return {"path": str(path), "characters": len(body), "truncated": len(body) >= MAX_MEMORY_CHARS}


def persist_knowledge_update(root: Path, run_id: str, knowledge_delta: dict[str, Any], next_research: list[dict[str, Any]]) -> dict[str, Any]:
    known_evidence = {str(item.get("id")) for _, item in iter_jsonl(root / "evidence/cards.jsonl") if item.get("id")}; errors = validate_knowledge_delta(knowledge_delta) + validate_next_research(next_research, known_evidence)
    if errors: raise ValueError("; ".join(sorted(set(errors))))
    append_jsonl(root / "memory/knowledge-deltas.jsonl", [{"run_id": run_id, "created_at": utc_now(), "knowledge_delta": knowledge_delta}]); backlog = {"schema_version": 1, "generated_from_run": run_id, "generated_at": utc_now(), "items": next_research}; atomic_write_json(root / "plans/research-backlog.json", backlog); memory = render_current_memory(root)
    return {"knowledge_delta_recorded": True, "backlog_items": len(next_research), "backlog": str(root / "plans/research-backlog.json"), "memory": memory}
