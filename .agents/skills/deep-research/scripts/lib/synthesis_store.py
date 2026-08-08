from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import append_jsonl, atomic_write_json, iter_jsonl, utc_now
from .research_memory import render_current_memory, validate_knowledge_delta, validate_next_research


def persist_knowledge_update(root: Path, run_id: str, synthesis_id: str, knowledge_delta: dict[str, Any], next_research: list[dict[str, Any]]) -> dict[str, Any]:
    known_evidence = {str(item.get("id")) for _, item in iter_jsonl(root / "evidence/cards.jsonl") if item.get("id")}
    errors = validate_knowledge_delta(knowledge_delta) + validate_next_research(next_research, known_evidence)
    if errors: raise ValueError("; ".join(sorted(set(errors))))
    delta_path = root / "memory/knowledge-deltas.jsonl"
    already_recorded = any(item.get("synthesis_id") == synthesis_id for _, item in iter_jsonl(delta_path))
    if not already_recorded:
        append_jsonl(delta_path, [{"synthesis_id": synthesis_id, "run_id": run_id, "created_at": utc_now(), "knowledge_delta": knowledge_delta}])
    backlog = {"schema_version": 1, "generated_from_run": run_id, "generated_from_synthesis": synthesis_id, "generated_at": utc_now(), "items": next_research}
    atomic_write_json(root / "plans/research-backlog.json", backlog); memory = render_current_memory(root)
    return {"knowledge_delta_recorded": not already_recorded, "knowledge_delta_already_recorded": already_recorded, "backlog_items": len(next_research), "backlog": str(root / "plans/research-backlog.json"), "memory": memory}
