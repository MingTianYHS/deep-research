#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.io_utils import atomic_write_json, iter_jsonl
from lib.report_rubric import evaluate_report, load_rubric

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parents[2]
WORKSPACE_ROOT = REPO_ROOT / "workspace/topics"
RUBRIC = SKILL_DIR / "config/report_rubric.toml"


def cmd_report(args):
    root = WORKSPACE_ROOT / args.slug
    if not root.exists(): raise SystemExit(f"topic not found: {args.slug}")
    evidence = {card["id"]: card for _, card in iter_jsonl(root / "evidence/cards.jsonl") if card.get("id")}
    result = evaluate_report(Path(args.report), evidence, load_rubric(RUBRIC))
    if args.output: atomic_write_json(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_gates and not result["passes_all_gates"]: raise SystemExit(1)


def parser():
    p = argparse.ArgumentParser(prog="evalctl"); sub = p.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report-check"); report.add_argument("slug"); report.add_argument("--report", required=True); report.add_argument("--output"); report.add_argument("--require-gates", action="store_true"); report.set_defaults(func=cmd_report)
    return p


if __name__ == "__main__":
    args = parser().parse_args(); args.func(args)
