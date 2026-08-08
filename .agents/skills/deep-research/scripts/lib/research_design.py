from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

QUESTION_TYPES = {"fact", "comparison", "causal", "forecast", "decision", "landscape"}
WORKER_PROFILES = {"lite", "standard", "deep"}
PROFILE_QUESTION_LIMITS = {"lite": 4, "standard": 6, "deep": 8}
QUESTION_STATUSES = {"open", "closed", "deferred"}
REQUIRED = {"id", "question", "type", "decision_relevance", "acceptance_criteria", "disconfirming_query", "overlap_key"}


def validate_design(design: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    questions = design.get("questions")
    if not isinstance(questions, list) or not questions:
        return {"valid": False, "errors": ["questions must be a non-empty list"], "warnings": [], "question_count": 0, "parallel_groups": []}
    maximum = PROFILE_QUESTION_LIMITS.get(profile, 8)
    if len(questions) > maximum: errors.append(f"profile {profile or 'deep'} allows at most {maximum} research questions")
    ids = [item.get("id") for item in questions]
    duplicates = [value for value, count in Counter(ids).items() if value and count > 1]
    if duplicates: errors.append(f"duplicate question ids: {duplicates}")
    known = set(ids)
    overlap = Counter(item.get("overlap_key") for item in questions if item.get("overlap_key"))
    for index, item in enumerate(questions, 1):
        if not isinstance(item, dict): errors.append(f"question {index}: must be an object"); continue
        missing = sorted(key for key in REQUIRED if not item.get(key))
        if missing: errors.append(f"question {index}: missing {missing}")
        if item.get("type") not in QUESTION_TYPES: errors.append(f"question {index}: invalid type {item.get('type')}")
        if item.get("status", "open") not in QUESTION_STATUSES: errors.append(f"question {index}: invalid status {item.get('status')}")
        criteria = item.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria: errors.append(f"question {index}: acceptance_criteria must be a non-empty list")
        dependencies = item.get("dependencies", [])
        if not isinstance(dependencies, list): errors.append(f"question {index}: dependencies must be a list")
        else:
            unknown = sorted(set(dependencies) - known)
            if unknown: errors.append(f"question {index}: unknown dependencies {unknown}")
            if item.get("id") in dependencies: errors.append(f"question {index}: self dependency")
        if overlap[item.get("overlap_key")] > 1: errors.append(f"question {index}: duplicate overlap_key {item.get('overlap_key')}")
        if item.get("type") in {"causal", "forecast"} and not item.get("alternative_explanations"): warnings.append(f"question {index}: causal/forecast question should list alternative_explanations")
        if not item.get("preferred_source_types"): warnings.append(f"question {index}: preferred_source_types not specified")
        worker_profile = item.get("worker_budget_profile", "standard")
        if worker_profile not in WORKER_PROFILES: errors.append(f"question {index}: invalid worker_budget_profile {worker_profile}")
        if item.get("version_sensitive"):
            if not item.get("target_version") and not item.get("target_commit"): errors.append(f"question {index}: version_sensitive requires target_version or target_commit")
            if item.get("target_version") in {"main", "latest"}: warnings.append(f"question {index}: target_version should identify an installed or released version, not {item.get('target_version')}")
        elif item.get("target_version") or item.get("target_commit"): warnings.append(f"question {index}: target version supplied without version_sensitive=true")
    graph = {item.get("id"): item.get("dependencies", []) for item in questions if isinstance(item, dict) and item.get("id")}
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting: errors.append(f"dependency cycle includes {node}"); return
        if node in visited: return
        visiting.add(node)
        for dependency in graph.get(node, []): visit(dependency)
        visiting.remove(node); visited.add(node)
    for node in graph: visit(node)
    return {"valid": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "question_count": len(questions), "parallel_groups": parallel_groups(questions)}


def parallel_groups(questions: list[dict[str, Any]]) -> list[list[str]]:
    remaining = {item["id"]: set(item.get("dependencies", [])) for item in questions if isinstance(item, dict) and item.get("id") and item.get("status", "open") == "open"}
    completed = {item["id"] for item in questions if isinstance(item, dict) and item.get("id") and item.get("status") == "closed"}
    groups: list[list[str]] = []
    while remaining:
        ready = sorted(node for node, dependencies in remaining.items() if dependencies <= completed)
        if not ready: break
        groups.append(ready); completed.update(ready)
        for node in ready: remaining.pop(node)
    return groups


def _question(question_id: str, text: str, profile: str) -> dict[str, Any]:
    return {"id": question_id, "status": "open", "question": text, "type": "fact", "decision_relevance": "Why the answer matters", "dependencies": [], "overlap_key": f"incremental-{question_id}", "preferred_source_types": ["official", "paper"], "acceptance_criteria": ["At least one primary source", "Independent corroboration for a core claim"], "disconfirming_query": f"Find credible evidence that contradicts or materially narrows: {text}", "alternative_explanations": [], "exclusions": [], "version_sensitive": False, "target_version": "", "target_commit": "", "allow_main_branch_fallback": False, "worker_budget_profile": profile}


def incremental_design(title: str, question: str, worker_budget_profile: str, backlog_item: dict[str, Any] | None = None) -> dict[str, Any]:
    if worker_budget_profile not in WORKER_PROFILES: raise ValueError(f"invalid worker budget profile: {worker_budget_profile}")
    text = " ".join(str(question or "").split())
    if not text: raise ValueError("incremental research question must not be empty")
    source = backlog_item if isinstance(backlog_item, dict) else {}
    digest = hashlib.sha256(text.casefold().encode("utf-8")).hexdigest()[:10]
    item = _question(f"q-inc-{digest}", text, worker_budget_profile)
    criteria = source.get("acceptance_criteria")
    if isinstance(criteria, list) and any(str(value).strip() for value in criteria): item["acceptance_criteria"] = [str(value).strip() for value in criteria if str(value).strip()]
    item["decision_relevance"] = str(source.get("reason") or "Update the topic's current understanding for this user-selected gap.")
    return {"title": title, "design_mode": "incremental", "decision_context": f"User-selected incremental research: {text}", "scope": {"include": [text], "exclude": [], "time_window": "", "geographies": []}, "incremental_source": {"backlog_id": source.get("id"), "known_evidence_ids": list(source.get("known_evidence_ids", [])) if isinstance(source.get("known_evidence_ids"), list) else [], "gap_type": source.get("gap_type")}, "questions": [item]}


def template(title: str, question_count: int = 1, worker_budget_profile: str = "standard") -> dict[str, Any]:
    if worker_budget_profile not in WORKER_PROFILES: raise ValueError(f"invalid worker budget profile: {worker_budget_profile}")
    maximum = PROFILE_QUESTION_LIMITS[worker_budget_profile]
    if not 1 <= question_count <= maximum: raise ValueError(f"profile {worker_budget_profile} allows 1-{maximum} research questions")
    questions = []
    for index in range(1, question_count + 1):
        item = _question(f"q-{index:03d}", f"Replace with answerable research question {index}", worker_budget_profile)
        item["overlap_key"] = f"unique-subtopic-{index}"; item["disconfirming_query"] = "Search terms intended to disprove the expected answer"
        questions.append(item)
    return {"title": title, "design_mode": "baseline", "decision_context": "What decision or understanding should this research support?", "scope": {"include": [], "exclude": [], "time_window": "", "geographies": []}, "questions": questions}


def render_questions(design: dict[str, Any]) -> str:
    lines = ["# Research questions", ""]
    for item in design.get("questions", []):
        lines += [f"## {item.get('id')}", "", f"- Status: {item.get('status', 'open')}", f"- Type: {item.get('type')}", f"- Question: {item.get('question')}", f"- Decision relevance: {item.get('decision_relevance')}", f"- Overlap key: {item.get('overlap_key')}", ""]
    return "\n".join(lines).rstrip() + "\n"
