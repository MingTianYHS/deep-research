#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.rollout_audit import audit_rollout
from lib.runtime_preflight import diagnose
from lib.source_attempts import append_attempt, assess_response, build_attempt, may_attempt
from lib.worker_contract import profile_limits, validate_worker_result

SKILL_DIR = Path(__file__).resolve().parent.parent
USER_ROOT = SKILL_DIR.parents[2]
DEFAULT_WORKSPACE = USER_ROOT / "workspace" / "topics"


def _workspace() -> Path:
    import os
    value = os.environ.get("DEEP_RESEARCH_WORKSPACE_ROOT", "").strip()
    return Path(os.path.expandvars(value)).expanduser() if value else DEFAULT_WORKSPACE


def cmd_doctor(args: argparse.Namespace) -> None:
    result = diagnose(SKILL_DIR, Path(args.workspace).expanduser() if args.workspace else _workspace())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not result["valid"]: raise SystemExit(1)


def cmd_validate_worker(args: argparse.Namespace) -> None:
    result = json.loads(Path(args.file).read_text(encoding="utf-8"))
    outcome = validate_worker_result(result, profile_limits(args.profile))
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    if args.require_gates and not outcome["valid"]: raise SystemExit(1)


def cmd_rollout(args: argparse.Namespace) -> None:
    result = audit_rollout(Path(args.file), max_tool_calls=args.max_tool_calls, max_failed_calls=args.max_failed_calls)
    if args.output: Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_gates and not result["passes_all_gates"]: raise SystemExit(1)


def cmd_source_check(args: argparse.Namespace) -> None:
    content = Path(args.content_file).read_text(encoding="utf-8", errors="replace")
    result = assess_response(args.http_status, content)
    if args.url:
        result = build_attempt(args.url, args.tool, args.http_status, content, source_version=args.source_version)
        if args.log:
            log = Path(args.log); decision = may_attempt(log, args.url, args.max_attempts); result["attempt_decision"] = decision
            if decision["allowed"]:
                result = append_attempt(log, result); result["attempt_decision"] = decision
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_eligible and not result["eligible_for_evidence"]: raise SystemExit(1)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="runtimectl"); sub = p.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor"); doctor.add_argument("--workspace"); doctor.add_argument("--strict", action="store_true"); doctor.set_defaults(func=cmd_doctor)
    worker = sub.add_parser("validate-worker"); worker.add_argument("--file", required=True); worker.add_argument("--profile", choices=["lite", "standard", "deep"], default="standard"); worker.add_argument("--require-gates", action="store_true"); worker.set_defaults(func=cmd_validate_worker)
    rollout = sub.add_parser("rollout-audit"); rollout.add_argument("--file", required=True); rollout.add_argument("--output"); rollout.add_argument("--max-tool-calls", type=int, default=24); rollout.add_argument("--max-failed-calls", type=int, default=3); rollout.add_argument("--require-gates", action="store_true"); rollout.set_defaults(func=cmd_rollout)
    source = sub.add_parser("source-check"); source.add_argument("--content-file", required=True); source.add_argument("--http-status", type=int); source.add_argument("--url"); source.add_argument("--tool", default="unknown"); source.add_argument("--source-version"); source.add_argument("--log"); source.add_argument("--max-attempts", type=int, default=2); source.add_argument("--require-eligible", action="store_true"); source.set_defaults(func=cmd_source_check)
    return p


if __name__ == "__main__":
    args = parser().parse_args(); args.func(args)
