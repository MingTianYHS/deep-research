#!/usr/bin/env python3
"""Unified user-facing workflow entry point for the persistent research assistant."""
from __future__ import annotations

import argparse
import contextlib
import io
import json

import researchctl
import topicctl
from lib.coordinator_budget import consume_next_call
from lib.coordinator_lease import acquire_or_refresh, resolve_coordinator_id
from lib.io_utils import read_json
from lib.lean_claims import sync_run_claims
from lib.lean_workflow import derive_workflow
from lib.research_memory import load_backlog


def cmd_new(args: argparse.Namespace) -> None: topicctl.cmd_init(argparse.Namespace(title=args.title, directory_name=args.directory_name, budget=args.budget, force=False, allow_language_mismatch=args.allow_language_mismatch))
def cmd_plan(args: argparse.Namespace) -> None: researchctl.cmd_plan(argparse.Namespace(slug=args.topic, questions=args.questions, force=False))
def cmd_brief(args: argparse.Namespace) -> None: researchctl.cmd_brief(argparse.Namespace(slug=args.topic, question=args.question, output=args.output))
def cmd_start(args: argparse.Namespace) -> None: researchctl.cmd_run_start(argparse.Namespace(slug=args.topic, mode=args.mode))
def cmd_continue(args: argparse.Namespace) -> None: researchctl.cmd_continue(argparse.Namespace(slug=args.topic, backlog_id=args.backlog_id, question=args.question))
def cmd_status(args: argparse.Namespace) -> None: researchctl.cmd_status(argparse.Namespace(slug=args.topic))


def _budget_exhausted(result: dict, budget: dict) -> dict:
    return {**result, "phase": "coordinator_budget_exhausted", "next_action": "request_budget_decision", "command": None, "agent": None, "assignments": [], "requires_user_input": True, "blockers": budget["violations"], "coordinator_budget": budget, "coordinator_instruction": "Stop automatic orchestration. Ask the user whether to finish partial, inspect the repeated phase, or explicitly continue with a larger topic profile."}


def _lease_blocked(run_id: str, lease: dict) -> dict:
    return {"workflow_schema_version": 2, "active_run_id": run_id, "phase": "coordinator_lease_blocked", "next_action": "use_active_coordinator_or_wait_for_lease", "command": None, "agent": None, "requires_user_input": True, "blockers": [lease["violation"]], "assignments": [], "progress": {}, "coordinator_lease": lease, "coordinator_instruction": "Do not continue from this session while another coordinator owns the active topic lease."}


def _wait_for_user(root, result: dict) -> dict:
    backlog = load_backlog(root)["items"]
    return {**result, "phase": "awaiting_user_research_request", "next_action": "present_memory_and_backlog_then_wait", "command": None, "agent": None, "requires_user_input": True, "blockers": [], "assignments": [], "progress": {**dict(result.get("progress") or {}), "next_research": backlog}, "coordinator_instruction": "Present the current findings and bounded follow-up backlog, then stop. Use research.py continue only after the user explicitly selects a backlog item or asks a new research question."}


def cmd_next(args: argparse.Namespace) -> None:
    root = researchctl.topic_dir(args.topic); state = read_json(root / "state.json", {}); state_run_id = state.get("active_run_id"); lease = None
    if state_run_id:
        lease = acquire_or_refresh(root, str(state_run_id), resolve_coordinator_id(getattr(args, "coordinator_id", None)))
        if not lease["allowed"]: print(json.dumps(_lease_blocked(str(state_run_id), lease), ensure_ascii=False, indent=2)); return
    result = derive_workflow(root, researchctl.SKILL_DIR)
    if not state_run_id and state.get("last_run_at") and result.get("phase") in {"ready_to_start", "reflection", "reflection_blocked"}: result = _wait_for_user(root, result)
    run_id = result.get("active_run_id")
    if lease is not None: result["coordinator_lease"] = lease
    if run_id:
        profile = str(state.get("budget_profile") or "standard"); budget = consume_next_call(root, str(run_id), profile, str(result.get("phase") or "unknown"), str(result.get("next_action") or "unknown"), researchctl.SKILL_DIR / "config/orchestration.toml"); result["coordinator_budget"] = budget
        if not budget["allowed"]: result = _budget_exhausted(result, budget)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_claim_sync(args: argparse.Namespace) -> None:
    root = researchctl.topic_dir(args.topic); state = read_json(root / "state.json", {}); run_id = state.get("active_run_id")
    if not run_id: raise SystemExit("claim-sync requires an active run")
    if str(state.get("budget_profile") or "standard") == "deep": raise SystemExit("deep profile requires explicit Claim review")
    print(json.dumps(sync_run_claims(root, str(run_id)), ensure_ascii=False, indent=2))


def cmd_report(args: argparse.Namespace) -> None: topicctl.cmd_report(argparse.Namespace(topic=args.topic, type=args.type, title=args.title, output=args.output, allow_language_mismatch=args.allow_language_mismatch))
def cmd_finish(args: argparse.Namespace) -> None: researchctl.cmd_run_finish(argparse.Namespace(slug=args.topic, status=args.status, note=args.note))


def cmd_validate(args: argparse.Namespace) -> None:
    naming = topicctl.naming_result(args.topic, args.allow_language_mismatch)
    if not naming["valid"]:
        result = {"valid": False, "topic": naming["topic"], "workspace": naming["workspace"], "errors": naming["errors"], "warnings": []}; print(json.dumps(result, ensure_ascii=False, indent=2)); raise SystemExit(1)
    output = io.StringIO(); exit_code = 0
    with contextlib.redirect_stdout(output):
        try: researchctl.cmd_validate(argparse.Namespace(slug=args.topic))
        except SystemExit as exc: exit_code = int(exc.code or 1)
    try: structural = json.loads(output.getvalue())
    except json.JSONDecodeError as exc: raise SystemExit("internal validation returned invalid JSON") from exc
    structural["topic"] = naming["topic"]; structural["workspace"] = naming["workspace"]; print(json.dumps(structural, ensure_ascii=False, indent=2))
    if exit_code or not structural.get("valid", False): raise SystemExit(exit_code or 1)


def _topic_argument(parser: argparse.ArgumentParser) -> None: parser.add_argument("topic", nargs="?", help="Topic directory/name. Omit inside a topic workspace.")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="research", description="User-directed persistent research assistant for one topic."); sub = value.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="Create one persistent topic workspace."); new.add_argument("title"); new.add_argument("--directory-name"); new.add_argument("--budget", choices=["lite", "standard", "deep"], default="standard"); new.add_argument("--allow-language-mismatch", action="store_true"); new.set_defaults(func=cmd_new)
    plan = sub.add_parser("plan", help="Create or synchronize the baseline Research Design."); _topic_argument(plan); plan.add_argument("--questions", type=int, default=5, choices=range(1, 9)); plan.set_defaults(func=cmd_plan)
    brief = sub.add_parser("brief", help="Recall bounded knowledge, sources, prior queries, and gaps before searching."); _topic_argument(brief); brief.add_argument("--question"); brief.add_argument("--output"); brief.set_defaults(func=cmd_brief)
    start = sub.add_parser("start", help="Start the prepared baseline or incremental Run."); _topic_argument(start); start.add_argument("--mode", choices=["baseline", "initial", "incremental"], default="initial"); start.set_defaults(func=cmd_start)
    continuation = sub.add_parser("continue", help="Turn one user-selected gap into a bounded incremental Run."); _topic_argument(continuation); group = continuation.add_mutually_exclusive_group(required=True); group.add_argument("--backlog-id"); group.add_argument("--question"); continuation.set_defaults(func=cmd_continue)
    status = sub.add_parser("status", help="Show topic state, record counts, and follow-up backlog."); _topic_argument(status); status.set_defaults(func=cmd_status)
    next_step = sub.add_parser("next", help="Return the next legal action; never starts another Run after delivery without the user."); _topic_argument(next_step); next_step.add_argument("--coordinator-id", help="Stable identity for enforcing one coordinator per topic run"); next_step.set_defaults(func=cmd_next)
    claim_sync = sub.add_parser("claim-sync", help="Materialize compact Claims for a lite/standard run."); _topic_argument(claim_sync); claim_sync.set_defaults(func=cmd_claim_sync)
    report = sub.add_parser("report", help="Create a report inside the canonical topic workspace."); _topic_argument(report); report.add_argument("--type", choices=["initial", "update", "final"], default="initial"); report.add_argument("--title"); report.add_argument("--output"); report.add_argument("--allow-language-mismatch", action="store_true"); report.set_defaults(func=cmd_report)
    finish = sub.add_parser("finish", help="Close the active Run after all required gates."); _topic_argument(finish); finish.add_argument("--status", choices=["complete", "partial", "failed"], default="complete"); finish.add_argument("--note", default=""); finish.set_defaults(func=cmd_finish)
    validate = sub.add_parser("validate", help="Validate naming, workspace, design, memory, and records."); _topic_argument(validate); validate.add_argument("--allow-language-mismatch", action="store_true"); validate.set_defaults(func=cmd_validate)
    return value


if __name__ == "__main__": arguments = parser().parse_args(); arguments.func(arguments)
