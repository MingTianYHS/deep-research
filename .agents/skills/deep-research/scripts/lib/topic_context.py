from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from .claims import materialize
from .io_utils import append_jsonl, atomic_write_json, iter_jsonl, read_json, utc_now
from .research_design import render_questions

LESSON_TYPES = {
    "source_strategy",
    "failed_route",
    "query_strategy",
    "scope_trap",
    "version_trap",
    "independence_trap",
    "user_correction",
    "quality_failure",
}
MAX_CONTEXT_CHARS = 12_000
MAX_BRIEF_CHARS = 16_000


def resolve_topic(workspace_root: Path, slug: str | None = None, cwd: Path | None = None) -> Path:
    if slug and slug not in {".", "./"}:
        candidate = Path(slug).expanduser()
        if candidate.is_absolute() and (candidate / "topic.toml").is_file():
            return candidate.resolve()
        root = workspace_root / slug
        if root.is_dir() and (root / "topic.toml").is_file():
            return root.resolve()
        raise FileNotFoundError(f"topic not found: {slug} (workspace root: {workspace_root})")
    current = (cwd or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "topic.toml").is_file():
            return candidate
    raise FileNotFoundError("no topic supplied and current directory is not inside a topic workspace")


def load_design(root: Path) -> dict[str, Any] | None:
    path = root / "plans/current-design.json"
    return read_json(path, None) if path.exists() else None


def load_lessons(root: Path, limit: int = 8) -> list[dict[str, Any]]:
    items = [
        item
        for _, item in iter_jsonl(root / "memory/lessons.jsonl")
        if item.get("status", "active") == "active"
    ]
    return items[-limit:]


def _clip(value: Any, maximum: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= maximum else text[: maximum - 1].rstrip() + "…"


def _clip_list(value: Any, count: int, item_chars: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clip(item, item_chars) for item in value[:count] if str(item).strip()]


def _bounded_question(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _clip(item.get("id"), 80),
        "status": item.get("status", "open"),
        "question": _clip(item.get("question"), 600),
        "type": item.get("type"),
        "decision_relevance": _clip(item.get("decision_relevance"), 400),
        "dependencies": _clip_list(item.get("dependencies"), 8, 80),
        "overlap_key": _clip(item.get("overlap_key"), 160),
        "preferred_source_types": _clip_list(item.get("preferred_source_types"), 6, 80),
        "acceptance_criteria": _clip_list(item.get("acceptance_criteria"), 5, 300),
        "disconfirming_query": _clip(item.get("disconfirming_query"), 400),
        "target_version": _clip(item.get("target_version"), 100),
        "target_commit": _clip(item.get("target_commit"), 100),
        "worker_budget_profile": item.get("worker_budget_profile", "standard"),
    }


def _known_urls(root: Path, limit: int = 24) -> list[str]:
    urls: list[str] = []
    for _, card in iter_jsonl(root / "evidence/cards.jsonl"):
        source = card.get("source") or {}
        url = source.get("canonical_url") or source.get("url")
        if url:
            bounded = _clip(url, 1_000)
            if bounded not in urls:
                urls.append(bounded)
    return urls[-limit:]


def _bounded_scope(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "include": _clip_list(value.get("include"), 12, 200),
        "exclude": _clip_list(value.get("exclude"), 12, 200),
        "time_window": _clip(value.get("time_window"), 200),
        "geographies": _clip_list(value.get("geographies"), 12, 100),
    }


def _trim_brief(brief: dict[str, Any]) -> dict[str, Any]:
    def size() -> int:
        return len(json.dumps(brief, ensure_ascii=False, sort_keys=True))

    for key in ("known_urls", "priority_claims", "lessons"):
        while size() > MAX_BRIEF_CHARS and brief[key]:
            brief[key].pop(0)
    if size() > MAX_BRIEF_CHARS:
        raise ValueError(f"bounded topic brief exceeds {MAX_BRIEF_CHARS} characters")
    return brief


def build_brief(root: Path, question_id: str | None = None) -> dict[str, Any]:
    state = read_json(root / "state.json", {})
    claims = materialize(root / "claims.jsonl")
    design = load_design(root)
    questions = (design or {}).get("questions", [])
    parent_mode = "incremental" if state.get("baseline_completed") else "baseline"
    mode = parent_mode
    if question_id:
        questions = [item for item in questions if item.get("id") == question_id]
        if not questions:
            raise ValueError(f"question not found in current design: {question_id}")
        mode = "question"
    priority = [
        {
            "id": item.get("id"),
            "text": _clip(item.get("text"), 500),
            "status": item.get("status"),
            "confidence": item.get("confidence"),
        }
        for item in claims.values()
        if item.get("status") in {"contested", "unresolved"} or item.get("pending_transition")
    ][:10]
    lessons = [
        {
            "id": item.get("id"),
            "type": item.get("type"),
            "scope": _clip(item.get("scope"), 200),
            "lesson": _clip(item.get("lesson"), 500),
            "run_id": item.get("run_id"),
        }
        for item in load_lessons(root)
    ]
    instructions = [
        "Do not treat this brief or context.md as evidence.",
        "Use Claim/Evidence IDs to load supporting material only when relevant.",
        "For a baseline run, establish scope and primary sources without assuming prior expertise."
        if parent_mode == "baseline"
        else "Search unresolved questions, contested claims, and material changes since the last run.",
        "Stop at acceptance criteria and the configured worker budget.",
    ]
    if mode == "question":
        instructions.insert(2, "Answer only the selected question and preserve its overlap boundary.")
    brief = {
        "topic": state.get("topic"),
        "workspace": str(root),
        "mode": mode,
        "parent_mode": parent_mode,
        "research_generation": int(state.get("research_generation", 0)),
        "last_run_at": state.get("last_run_at"),
        "budget_profile": state.get("budget_profile", "standard"),
        "scope": _bounded_scope((design or {}).get("scope", {})),
        "questions": [_bounded_question(item) for item in questions[:8]],
        "open_questions": _clip_list(state.get("open_questions"), 8, 80),
        "priority_claims": priority,
        "known_urls": _known_urls(root),
        "lessons": lessons,
        "instructions": instructions,
    }
    return _trim_brief(brief)


def render_context(root: Path, brief: dict[str, Any]) -> dict[str, Any]:
    lines = [
        "# 当前主题上下文",
        "",
        "> 此文件是从状态、Research Design、Claim 和 Lessons 生成的有界缓存，不是证据源。",
        "",
        "## 状态",
        "",
        f"- Topic: `{brief.get('topic')}`",
        f"- Mode: `{brief.get('mode')}`",
        f"- Research generation: `{brief.get('research_generation')}`",
        f"- Last run: `{brief.get('last_run_at')}`",
        "",
        "## 当前问题",
        "",
    ]
    for item in brief.get("questions", []):
        lines.append(f"- `{item.get('id')}` [{item.get('status')}] {item.get('question')}")
    if not brief.get("questions"):
        lines.append("- 尚未建立当前 Research Design。")
    lines += ["", "## 优先 Claim", ""]
    for item in brief.get("priority_claims", []):
        lines.append(f"- `{item.get('id')}` [{item.get('status')}] {item.get('text')}")
    if not brief.get("priority_claims"):
        lines.append("- 暂无 contested/unresolved Claim。")
    lines += ["", "## 已验证研究经验", ""]
    for item in brief.get("lessons", []):
        lines.append(f"- `{item.get('type')}` {item.get('lesson')}")
    if not brief.get("lessons"):
        lines.append("- 暂无。")
    lines += ["", "## 下一步", ""] + [f"- {item}" for item in brief.get("instructions", [])]
    body = "\n".join(lines).strip() + "\n"
    truncated = len(body) > MAX_CONTEXT_CHARS
    if truncated:
        marker = "\n\n> 上下文已按字符预算截断；按需通过 Claim/Evidence ID 加载原始记录。\n"
        body = body[: MAX_CONTEXT_CHARS - len(marker)].rstrip() + marker
    path = root / "context.md"
    path.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(json.dumps(brief, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    state = read_json(root / "state.json", {})
    state["context_generated_at"] = utc_now()
    state["context_brief_sha256"] = digest
    atomic_write_json(root / "state.json", state)
    return {
        "path": str(path),
        "characters": len(body),
        "brief_sha256": digest,
        "truncated": truncated,
    }


def validate_reflection(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for key in ("run_id", "summary", "open_questions", "next_actions", "lesson_candidates"):
        if key not in value:
            errors.append(f"missing {key}")
    if not isinstance(value.get("run_id"), str) or not value.get("run_id", "").strip():
        errors.append("run_id must be a non-empty string")
    if not isinstance(value.get("summary"), str) or not value.get("summary", "").strip():
        errors.append("summary must be a non-empty string")
    elif len(value["summary"]) > 2_000:
        errors.append("summary exceeds 2000 characters")
    for key, maximum in (("open_questions", 8), ("next_actions", 12), ("lesson_candidates", 12)):
        if key in value and not isinstance(value[key], list):
            errors.append(f"{key} must be a list")
        elif isinstance(value.get(key), list) and len(value[key]) > maximum:
            errors.append(f"{key} allows at most {maximum} items")
    for key in ("open_questions", "next_actions"):
        for index, item in enumerate(value.get(key, []) if isinstance(value.get(key), list) else [], 1):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"{key} item {index} must be a non-empty string")
    lessons = value.get("lesson_candidates", []) if isinstance(value.get("lesson_candidates"), list) else []
    for index, lesson in enumerate(lessons, 1):
        if not isinstance(lesson, dict):
            errors.append(f"lesson {index} must be an object")
            continue
        if lesson.get("type") not in LESSON_TYPES:
            errors.append(f"lesson {index}: invalid type")
        if not isinstance(lesson.get("lesson"), str) or not lesson.get("lesson", "").strip():
            errors.append(f"lesson {index}: missing lesson")
        elif len(lesson["lesson"]) > 1_000:
            errors.append(f"lesson {index}: exceeds 1000 characters")
        if lesson.get("validated_by") != "research_critic":
            errors.append(f"lesson {index}: validated_by must be research_critic")
    return {"valid": not errors, "errors": sorted(set(errors))}


def _finished_run(root: Path, run_id: str) -> tuple[str | None, bool]:
    status: str | None = None
    reflected = False
    for _, event in iter_jsonl(root / "logs/runs.jsonl"):
        if event.get("id") != run_id:
            continue
        if event.get("type") == "run.reflected":
            reflected = True
        if event.get("finished_at") and event.get("status") in {"complete", "partial", "failed"}:
            status = event["status"]
    return status, reflected


def apply_reflection(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    validation = validate_reflection(value)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    run_status, reflected = _finished_run(root, value["run_id"])
    if reflected:
        raise ValueError(f"run already reflected: {value['run_id']}")
    if not run_status:
        raise ValueError(f"reflection requires a finished run: {value['run_id']}")
    design = load_design(root)
    if design:
        known = {item.get("id") for item in design.get("questions", [])}
        unknown = sorted(set(value["open_questions"]) - known)
        if unknown:
            raise ValueError(f"reflection contains questions outside current design: {unknown}")
        open_ids = set(value["open_questions"])
        for item in design.get("questions", []):
            item["status"] = "open" if item.get("id") in open_ids else "closed"
        atomic_write_json(root / "plans/current-design.json", design)
        (root / "questions.md").write_text(render_questions(design), encoding="utf-8")
    path = root / "memory/lessons.jsonl"
    existing = {
        (
            item.get("type"),
            str(item.get("scope", "")),
            " ".join(str(item.get("lesson", "")).lower().split()),
        )
        for _, item in iter_jsonl(path)
    }
    accepted = []
    for raw in value["lesson_candidates"]:
        key = (
            raw["type"],
            str(raw.get("scope", "")),
            " ".join(raw["lesson"].lower().split()),
        )
        if key in existing:
            continue
        existing.add(key)
        accepted.append(
            {
                "id": raw.get("id") or f"lesson-{uuid.uuid4().hex[:12]}",
                "type": raw["type"],
                "scope": _clip(raw.get("scope"), 300),
                "lesson": raw["lesson"].strip(),
                "run_id": value["run_id"],
                "validated_by": "research_critic",
                "status": "active",
                "created_at": utc_now(),
            }
        )
    append_jsonl(path, accepted)
    state = read_json(root / "state.json", {})
    if run_status == "complete":
        state["baseline_completed"] = True
    state["research_generation"] = int(state.get("research_generation", 0)) + 1
    state["knowledge_status"] = "evolving" if run_status != "failed" else state.get("knowledge_status", "empty")
    state["open_questions"] = value["open_questions"]
    state["next_actions"] = value["next_actions"]
    reflected_at = utc_now()
    state["last_reflection"] = {
        "run_id": value["run_id"],
        "run_status": run_status,
        "summary": value["summary"].strip(),
        "at": reflected_at,
    }
    atomic_write_json(root / "state.json", state)
    context = render_context(root, build_brief(root))
    append_jsonl(
        root / "logs/runs.jsonl",
        [
            {
                "id": value["run_id"],
                "type": "run.reflected",
                "summary": value["summary"].strip(),
                "run_status": run_status,
                "accepted_lessons": len(accepted),
                "at": reflected_at,
            }
        ],
    )
    return {
        "accepted_lessons": len(accepted),
        "research_generation": state["research_generation"],
        "run_status": run_status,
        "baseline_completed": state.get("baseline_completed", False),
        "context": context,
    }
