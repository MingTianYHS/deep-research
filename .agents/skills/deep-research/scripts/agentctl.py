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
from lib.research_memory import persist_knowledge_update


def _atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            if not value.endswith("\n"): handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name): os.unlink(temp_name)


def cmd_synthesis_save(args: argparse.Namespace) -> None:
    root = researchctl.topic_dir(args.topic)
    with researchctl.lock(root):
        state = read_json(root / "state.json", {}); run_id = state.get("active_run_id")
        if not run_id: raise SystemExit("synthesis save requires an active run")
        value = json.loads(Path(args.file).read_text(encoding="utf-8"))
        result = validate_synthesis_result(root, value, run_id)
        if not result["valid"]: raise SystemExit("invalid synthesis result: " + "; ".join(result["errors"]))
        synthesis_id = value["id"]; log_path = root / "logs/syntheses" / f"{synthesis_id}.json"
        if log_path.exists(): raise SystemExit(f"synthesis result already exists: {synthesis_id}")
        report_path = Path(value["report_path"]).expanduser().resolve(); wrote_report = value["status"] != "blocked"
        if wrote_report: _atomic_write_text(report_path, value["report_markdown"])
        report_sha256 = hashlib.sha256(value["report_markdown"].encode("utf-8")).hexdigest() if wrote_report else None
        memory = persist_knowledge_update(root, str(run_id), value["knowledge_delta"], value["next_research"])
        stored = {key: value[key] for key in ("synthesis_result_version", "id", "run_id", "critic_review_id", "input_snapshot", "status", "report_path", "output_language", "claim_ids_used", "evidence_ids_used", "unresolved", "knowledge_delta", "next_research")}
        stored.update(saved_at=utc_now(), report_sha256=report_sha256, wrote_report=wrote_report); atomic_write_json(log_path, stored)
    print(json.dumps({"valid": True, "synthesis_log": str(log_path), "report": str(report_path) if wrote_report else None, "report_sha256": report_sha256, "status": value["status"], "memory": memory, "next_research": value["next_research"]}, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="agentctl", description="Internal versioned subagent result control."); sub = value.add_subparsers(dest="command", required=True)
    synthesis = sub.add_parser("synthesis-save", help="Validate and persist SynthesisResult v2."); synthesis.add_argument("topic", nargs="?"); synthesis.add_argument("--file", required=True); synthesis.set_defaults(func=cmd_synthesis_save)
    return value


if __name__ == "__main__":
    arguments = parser().parse_args(); arguments.func(arguments)
