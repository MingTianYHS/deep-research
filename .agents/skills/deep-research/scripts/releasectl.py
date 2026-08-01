#!/usr/bin/env python3
"""Cost accounting, deterministic export, and release checks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.costs import record, summarize
from lib.package_export import export_topic, verify_package
from lib.release_check import check_repo

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parents[2]
WORKSPACE_ROOT = REPO_ROOT / "workspace/topics"


def topic_root(slug: str) -> Path:
    root = WORKSPACE_ROOT / slug
    if not root.exists():
        raise SystemExit(f"topic not found: {slug}")
    return root


def cmd_cost_record(args: argparse.Namespace) -> None:
    root = topic_root(args.slug)
    event = record(root / "logs/costs.jsonl", {"provider": args.provider, "operation": args.operation, "quantity": args.quantity, "unit": args.unit, "cost_usd": args.cost_usd, "estimated": args.estimated, "run_id": args.run_id, "metadata": {"note": args.note} if args.note else {}})
    print(json.dumps(event, ensure_ascii=False, indent=2))


def cmd_cost_summary(args: argparse.Namespace) -> None:
    result = summarize(topic_root(args.slug) / "logs/costs.jsonl", args.run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_export(args: argparse.Namespace) -> None:
    root = topic_root(args.slug)
    output = Path(args.output) if args.output else REPO_ROOT / "dist" / f"{args.slug}.deep-research.zip"
    print(json.dumps(export_topic(root, output), ensure_ascii=False, indent=2))


def cmd_verify_package(args: argparse.Namespace) -> None:
    result = verify_package(Path(args.package))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


def cmd_release_check(args: argparse.Namespace) -> None:
    result = check_repo(REPO_ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"] or (args.strict and result["warnings"]):
        raise SystemExit(1)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="releasectl")
    sub = p.add_subparsers(dest="command", required=True)
    record_cmd = sub.add_parser("cost-record"); record_cmd.add_argument("slug"); record_cmd.add_argument("--provider", required=True); record_cmd.add_argument("--operation", required=True); record_cmd.add_argument("--quantity", type=float, required=True); record_cmd.add_argument("--unit", required=True); record_cmd.add_argument("--cost-usd", type=float, required=True); record_cmd.add_argument("--run-id", required=True); record_cmd.add_argument("--estimated", action="store_true"); record_cmd.add_argument("--note"); record_cmd.set_defaults(func=cmd_cost_record)
    summary = sub.add_parser("cost-summary"); summary.add_argument("slug"); summary.add_argument("--run-id"); summary.set_defaults(func=cmd_cost_summary)
    export = sub.add_parser("export-topic"); export.add_argument("slug"); export.add_argument("--output"); export.set_defaults(func=cmd_export)
    verify = sub.add_parser("verify-package"); verify.add_argument("--package", required=True); verify.set_defaults(func=cmd_verify_package)
    release = sub.add_parser("release-check"); release.add_argument("--strict", action="store_true"); release.set_defaults(func=cmd_release_check)
    return p


if __name__ == "__main__":
    args = parser().parse_args()
    args.func(args)
