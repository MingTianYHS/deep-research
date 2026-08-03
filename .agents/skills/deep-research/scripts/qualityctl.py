#!/usr/bin/env python3
"""Quality scoring and quote-fidelity audit control plane."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from lib.audit import create_audit, validate_audit
from lib.io_utils import atomic_write_json, iter_jsonl, read_json
from lib.quality import evaluate, load_policy
from lib.workspace_paths import workspace_root

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parents[2]
WORKSPACE_ROOT = workspace_root(REPO_ROOT)
POLICY_FILE = SKILL_DIR / "config/source_policy.toml"


def root_for(slug: str) -> Path:
    root = WORKSPACE_ROOT / slug
    if not root.exists(): raise SystemExit(f"topic not found: {slug} (workspace root: {WORKSPACE_ROOT})")
    return root


def evidence_map(root: Path) -> dict[str, dict]: return {card["id"]: card for _, card in iter_jsonl(root / "evidence/cards.jsonl") if card.get("id")}
def source_attempt_map(root: Path) -> dict[str, dict]: return {item["id"]: item for _, item in iter_jsonl(root / "logs/source_attempts.jsonl") if item.get("id")}


def cmd_quality(args: argparse.Namespace) -> None:
    root = root_for(args.slug); cards = list(evidence_map(root).values()); result = evaluate(cards, load_policy(POLICY_FILE), date.fromisoformat(args.as_of) if args.as_of else None)
    question_ids = set(re.findall(r"^##\s+(q-[A-Za-z0-9_-]+)", (root / "questions.md").read_text(encoding="utf-8"), re.MULTILINE)); coverage = result["questions_covered"] / len(question_ids) if question_ids else 0.0
    policy = load_policy(POLICY_FILE); gates = policy["quality_gates"]; result["question_count"] = len(question_ids); result["question_coverage"] = round(coverage, 4)
    result["gates"] = {"minimum_card_score": result["average_score"] >= float(gates["minimum_card_score"]), "minimum_primary_source_ratio": result["primary_source_ratio"] >= float(gates["minimum_primary_source_ratio"]), "minimum_question_coverage": coverage >= float(gates["minimum_question_coverage"]), "maximum_high_risk_cards": len(result["high_risk_cards"]) <= int(gates["maximum_high_risk_cards"])}; result["passes_all_gates"] = all(result["gates"].values())
    if args.output: atomic_write_json(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_gates and not result["passes_all_gates"]: raise SystemExit(1)


def cmd_audit_init(args: argparse.Namespace) -> None:
    root = root_for(args.slug); report_path = Path(args.report); output = Path(args.output) if args.output else report_path.with_suffix(report_path.suffix + ".audit.json"); run_id = read_json(root / "state.json", {}).get("active_run_id")
    audit = create_audit(report_path, evidence_map(root), output, source_attempt_map(root), run_id=run_id); print(json.dumps({"audit": str(output), "run_id": run_id, "items": len(audit["items"])}, ensure_ascii=False, indent=2))


def cmd_audit_validate(args: argparse.Namespace) -> None:
    result = validate_audit(Path(args.audit), require_all_verified=args.final); print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]: raise SystemExit(1)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qualityctl"); sub = p.add_subparsers(dest="command", required=True)
    quality = sub.add_parser("quality-report"); quality.add_argument("slug"); quality.add_argument("--as-of"); quality.add_argument("--output"); quality.add_argument("--require-gates", action="store_true"); quality.set_defaults(func=cmd_quality)
    init = sub.add_parser("audit-init"); init.add_argument("slug"); init.add_argument("--report", required=True); init.add_argument("--output"); init.set_defaults(func=cmd_audit_init)
    validate = sub.add_parser("audit-validate"); validate.add_argument("--audit", required=True); validate.add_argument("--final", action="store_true"); validate.set_defaults(func=cmd_audit_validate)
    return p


if __name__ == "__main__": args = parser().parse_args(); args.func(args)
