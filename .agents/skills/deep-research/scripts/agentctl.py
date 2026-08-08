#!/usr/bin/env python3
"""Internal validation and persistence for versioned subagent results."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

import researchctl
from lib.agent_contracts import validate_synthesis_result
from lib.io_utils import atomic_write_json, read_json, utc_now
from lib.synthesis_store import persist_knowledge_update


def _atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            if not value.endswith("\n"): handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name): os.unlink(temp_name)


def _digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def cmd_synthesis_save(args: argparse.Namespace) -> None:
    root = researchctl.topic_dir(args.topic)
    with researchctl.lock(root):
        state = read_json(root / "state.json", {}); run_id = state.get("active_run_id")
        if not run_id: raise SystemExit("synthesis save requires an active run")
        value = json.loads(Path(args.file).read_text(encoding="utf-8")); result = validate_synthesis_result(root, value, run_id)
        if not result["valid"]: raise SystemExit("invalid synthesis result: " + "; ".join(result["errors"]))
        synthesis_id = value["id"]; input_sha256 = _digest(value); log_path = root / "logs/syntheses" / f"{synthesis_id}.json"; pending_path = root / "logs/syntheses" / f".{synthesis_id}.pending.json"
        if log_path.exists():
            stored = read_json(log_path, {})
            if stored.get("input_sha256") != input_sha256: raise SystemExit(f"synthesis id already exists with different content: {synthesis_id}")
            pending_path.unlink(missing_ok=True)
            print(json.dumps({"valid": True, "idempotent": True, "synthesis_log": str(log_path), "report": stored.get("report_path") if stored.get("wrote_report") else None, "report_sha256": stored.get("report_sha256"), "status": stored.get("status"), "memory_applied": stored.get("memory_applied", False)}, ensure_ascii=False, indent=2)); return
        if pending_path.exists():
            pending = read_json(pending_path, {})
            if pending.get("input_sha256") != input_sha256: raise SystemExit(f"pending synthesis transaction differs from retry: {synthesis_id}")
        else: atomic_write_json(pending_path, {"synthesis_id": synthesis_id, "run_id": run_id, "input_sha256": input_sha256, "status": "validated", "created_at": utc_now()})
        report_path = Path(value["report_path"]).expanduser().resolve(); wrote_report = value["status"] != "blocked"
        if wrote_report: _atomic_write_text(report_path, value["report_markdown"])
        report_sha256 = hashlib.sha256(value["report_markdown"].encode("utf-8")).hexdigest() if wrote_report else None
        if value["status"] == "blocked":
            memory = {"knowledge_delta_recorded": False, "backlog_items": 0, "reason": "blocked synthesis does not update canonical memory"}; memory_applied = False
        else:
            memory = persist_knowledge_update(root, str(run_id), synthesis_id, value["knowledge_delta"], value["next_research"]); memory_applied = True
        stored = {key: value[key] for key in ("synthesis_result_version", "id", "run_id", "critic_review_id", "input_snapshot", "status", "report_path", "output_language", "claim_ids_used", "evidence_ids_used", "unresolved", "knowledge_delta", "next_research")}
        stored.update(saved_at=utc_now(), input_sha256=input_sha256, report_sha256=report_sha256, wrote_report=wrote_report, memory_applied=memory_applied); atomic_write_json(log_path, stored); pending_path.unlink(missing_ok=True)
    print(json.dumps({"valid": True, "idempotent": False, "synthesis_log": str(log_path), "report": str(report_path) if wrote_report else None, "report_sha256": report_sha256, "status": value["status"], "memory_applied": memory_applied, "memory": memory, "next_research": value["next_research"] if memory_applied else []}, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="agentctl", description="Internal versioned subagent result control."); sub = value.add_subparsers(dest="command", required=True)
    synthesis = sub.add_parser("synthesis-save", help="Validate and persist SynthesisResult v2."); synthesis.add_argument("topic", nargs="?"); synthesis.add_argument("--file", required=True); synthesis.set_defaults(func=cmd_synthesis_save)
    return value


if __name__ == "__main__":
    arguments = parser().parse_args(); arguments.func(arguments)
