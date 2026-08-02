from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

from .claims import materialize
from .io_utils import append_jsonl, atomic_write_json, iter_jsonl, read_json, utc_now

LESSON_TYPES = {"source_strategy", "failed_route", "query_strategy", "scope_trap", "version_trap", "independence_trap", "user_correction", "quality_failure"}
MAX_CONTEXT_CHARS = 12_000


def resolve_topic(workspace_root: Path, slug: str | None = None, cwd: Path | None = None) -> Path:
    if slug and slug not in {".", "./"}:
        candidate = Path(slug).expanduser()
        if candidate.is_absolute() and (candidate / "topic.toml").is_file(): return candidate.resolve()
        root = workspace_root / slug
        if root.is_dir(): return root.resolve()
        raise FileNotFoundError(f"topic not found: {slug} (workspace root: {workspace_root})")
    current = (cwd or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "topic.toml").is_file(): return candidate
    raise FileNotFoundError("no topic supplied and current directory is not inside a topic workspace")


def load_design(root: Path) -> dict[str, Any] | None:
    path = root / "plans/current-design.json"
    return read_json(path, None) if path.exists() else None


def load_lessons(root: Path, limit: int = 12) -> list[dict[str, Any]]:
    items = [item for _, item in iter_jsonl(root / "memory/lessons.jsonl") if item.get("status", "active") == "active"]
    return items[-limit:]


def _known_urls(root: Path, limit: int = 50) -> list[str]:
    urls = []
    for _, card in iter_jsonl(root / "evidence/cards.jsonl"):
        source = card.get("source") or {}; url = source.get("canonical_url") or source.get("url")
        if url and url not in urls: urls.append(url)
    return urls[-limit:]


def build_brief(root: Path, question_id: str | None = None) -> dict[str, Any]:
    state = read_json(root / "state.json", {}); claims = materialize(root / "claims.jsonl"); design = load_design(root)
    questions = (design or {}).get("questions", [])
    if question_id:
        questions = [item for item in questions if item.get("id") == question_id]
        if not questions: raise ValueError(f"question not found in current design: {question_id}")
    priority = [{"id": item.get("id"), "text": item.get("text"), "status": item.get("status"), "confidence": item.get("confidence")} for item in claims.values() if item.get("status") in {"contested", "unresolved"} or item.get("pending_transition")]
    mode = "incremental" if state.get("baseline_completed") else "baseline"
    return {"topic": state.get("topic"), "workspace": str(root), "mode": mode, "research_generation": int(state.get("research_generation", 0)), "last_run_at": state.get("last_run_at"), "budget_profile": state.get("budget_profile", "standard"), "scope": (design or {}).get("scope", {}), "questions": questions, "open_questions": state.get("open_questions", []), "priority_claims": priority[:12], "known_urls": _known_urls(root), "lessons": load_lessons(root), "instructions": ["Do not treat this brief or context.md as evidence.", "Use Claim/Evidence IDs to load supporting material only when relevant.", "For a baseline run, establish scope and primary sources without assuming prior expertise." if mode == "baseline" else "Search unresolved questions, contested claims, and material changes since the last run.", "Stop at acceptance criteria and the configured worker budget."]}


def render_context(root: Path, brief: dict[str, Any]) -> dict[str, Any]:
    lines = ["# 当前主题上下文", "", "> 此文件是从状态、Research Design、Claim 和 Lessons 生成的有界缓存，不是证据源。", "", "## 状态", "", f"- Topic: `{brief.get('topic')}`", f"- Mode: `{brief.get('mode')}`", f"- Research generation: `{brief.get('research_generation')}`", f"- Last run: `{brief.get('last_run_at')}`", "", "## 当前问题", ""]
    for item in brief.get("questions", []): lines.append(f"- `{item.get('id')}` {item.get('question')}")
    if not brief.get("questions"): lines.append("- 尚未建立当前 Research Design。")
    lines += ["", "## 优先 Claim", ""]
    for item in brief.get("priority_claims", []): lines.append(f"- `{item.get('id')}` [{item.get('status')}] {item.get('text')}")
    if not brief.get("priority_claims"): lines.append("- 暂无 contested/unresolved Claim。")
    lines += ["", "## 已验证研究经验", ""]
    for item in brief.get("lessons", []): lines.append(f"- `{item.get('type')}` {item.get('lesson')}")
    if not brief.get("lessons"): lines.append("- 暂无。")
    lines += ["", "## 下一步", ""] + [f"- {item}" for item in brief.get("instructions", [])]
    body = "\n".join(lines).strip() + "\n"
    if len(body) > MAX_CONTEXT_CHARS: raise ValueError(f"generated context exceeds {MAX_CONTEXT_CHARS} characters")
    path = root / "context.md"; path.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(json.dumps(brief, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {"path": str(path), "characters": len(body), "brief_sha256": digest}


def validate_reflection(value: dict[str, Any]) -> dict[str, Any]:
    errors = []
    for key in ("run_id", "summary", "open_questions", "next_actions", "lesson_candidates"):
        if key not in value: errors.append(f"missing {key}")
    for key in ("open_questions", "next_actions", "lesson_candidates"):
        if key in value and not isinstance(value[key], list): errors.append(f"{key} must be a list")
    for index, lesson in enumerate(value.get("lesson_candidates", []) if isinstance(value.get("lesson_candidates"), list) else [], 1):
        if not isinstance(lesson, dict): errors.append(f"lesson {index} must be an object"); continue
        if lesson.get("type") not in LESSON_TYPES: errors.append(f"lesson {index}: invalid type")
        if not lesson.get("lesson"): errors.append(f"lesson {index}: missing lesson")
        if not lesson.get("validated_by"): errors.append(f"lesson {index}: missing validated_by")
    return {"valid": not errors, "errors": sorted(set(errors))}


def apply_reflection(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    validation = validate_reflection(value)
    if not validation["valid"]: raise ValueError("; ".join(validation["errors"]))
    path = root / "memory/lessons.jsonl"; existing = {(item.get("type"), str(item.get("scope", "")), " ".join(str(item.get("lesson", "")).lower().split())) for _, item in iter_jsonl(path)}; accepted = []
    for raw in value["lesson_candidates"]:
        key = (raw["type"], str(raw.get("scope", "")), " ".join(raw["lesson"].lower().split()))
        if key in existing: continue
        existing.add(key); accepted.append({"id": raw.get("id") or f"lesson-{uuid.uuid4().hex[:12]}", "type": raw["type"], "scope": raw.get("scope", ""), "lesson": raw["lesson"], "run_id": value["run_id"], "validated_by": raw["validated_by"], "status": "active", "created_at": utc_now()})
    append_jsonl(path, accepted)
    state = read_json(root / "state.json", {}); state["baseline_completed"] = True; state["research_generation"] = int(state.get("research_generation", 0)) + 1; state["knowledge_status"] = "evolving"; state["open_questions"] = value["open_questions"]; state["next_actions"] = value["next_actions"]; state["last_reflection"] = {"run_id": value["run_id"], "summary": value["summary"], "at": utc_now()}; atomic_write_json(root / "state.json", state)
    context = render_context(root, build_brief(root))
    return {"accepted_lessons": len(accepted), "research_generation": state["research_generation"], "context": context}
