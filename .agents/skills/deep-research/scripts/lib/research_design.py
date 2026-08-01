from __future__ import annotations

from collections import Counter
from typing import Any

QUESTION_TYPES = {"fact", "comparison", "causal", "forecast", "decision", "landscape"}
REQUIRED = {"id", "question", "type", "decision_relevance", "acceptance_criteria", "disconfirming_query", "overlap_key"}


def validate_design(design: dict[str, Any]) -> dict[str, Any]:
    errors, warnings = [], []
    questions = design.get("questions")
    if not isinstance(questions, list) or not questions:
        return {"valid": False, "errors": ["questions must be a non-empty list"], "warnings": [], "question_count": 0}
    if len(questions) > 8:
        errors.append("at most 8 research questions are allowed")
    ids = [item.get("id") for item in questions]
    duplicates = [value for value, count in Counter(ids).items() if value and count > 1]
    if duplicates: errors.append(f"duplicate question ids: {duplicates}")
    known = set(ids)
    overlap = Counter(item.get("overlap_key") for item in questions if item.get("overlap_key"))
    for index, item in enumerate(questions, 1):
        missing = sorted(key for key in REQUIRED if not item.get(key))
        if missing: errors.append(f"question {index}: missing {missing}")
        if item.get("type") not in QUESTION_TYPES: errors.append(f"question {index}: invalid type {item.get('type')}")
        criteria = item.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria: errors.append(f"question {index}: acceptance_criteria must be a non-empty list")
        dependencies = item.get("dependencies", [])
        if not isinstance(dependencies, list): errors.append(f"question {index}: dependencies must be a list")
        else:
            unknown = sorted(set(dependencies) - known)
            if unknown: errors.append(f"question {index}: unknown dependencies {unknown}")
            if item.get("id") in dependencies: errors.append(f"question {index}: self dependency")
        if overlap[item.get("overlap_key")] > 1: errors.append(f"question {index}: duplicate overlap_key {item.get('overlap_key')}")
        if item.get("type") in {"causal", "forecast"} and not item.get("alternative_explanations"):
            warnings.append(f"question {index}: causal/forecast question should list alternative_explanations")
        if not item.get("preferred_source_types"):
            warnings.append(f"question {index}: preferred_source_types not specified")
    graph = {item.get("id"): item.get("dependencies", []) for item in questions if item.get("id")}
    visiting, visited = set(), set()
    def visit(node: str) -> None:
        if node in visiting: errors.append(f"dependency cycle includes {node}"); return
        if node in visited: return
        visiting.add(node)
        for dependency in graph.get(node, []): visit(dependency)
        visiting.remove(node); visited.add(node)
    for node in graph: visit(node)
    return {"valid": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "question_count": len(questions), "parallel_groups": parallel_groups(questions)}


def parallel_groups(questions: list[dict[str, Any]]) -> list[list[str]]:
    remaining = {item["id"]: set(item.get("dependencies", [])) for item in questions if item.get("id")}
    completed, groups = set(), []
    while remaining:
        ready = sorted(node for node, dependencies in remaining.items() if dependencies <= completed)
        if not ready: break
        groups.append(ready); completed.update(ready)
        for node in ready: remaining.pop(node)
    return groups


def template(title: str) -> dict[str, Any]:
    return {"title": title, "decision_context": "What decision or understanding should this research support?", "scope": {"include": [], "exclude": [], "time_window": "", "geographies": []}, "questions": [{"id": "q-001", "question": "Replace with one answerable research question", "type": "fact", "decision_relevance": "Why the answer matters", "dependencies": [], "overlap_key": "unique-subtopic", "preferred_source_types": ["official", "paper"], "acceptance_criteria": ["At least one primary source", "Independent corroboration for a core claim"], "disconfirming_query": "Search terms intended to disprove the expected answer", "alternative_explanations": [], "exclusions": []}]}
