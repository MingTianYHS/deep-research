#!/usr/bin/env python3
"""Cost accounting, migrations, deterministic exports, and release checks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.costs import record, summarize
from lib.migrations import apply as apply_migration, inspect as inspect_workspace, plan as plan_migration
from lib.package_export import export_topic, verify_package
from lib.providers import load as load_providers, validate as validate_providers, validate_usage
from lib.release_check import check_repo

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parents[2]
WORKSPACE_ROOT = REPO_ROOT / "workspace/topics"
PROVIDERS_FILE = SKILL_DIR / "config/providers.toml"


def topic_root(slug: str) -> Path:
    root = WORKSPACE_ROOT / slug
    if not root.exists(): raise SystemExit(f"topic not found: {slug}")
    return root


def registry() -> dict:
    value = load_providers(PROVIDERS_FILE); errors = validate_providers(value)
    if errors: raise SystemExit("invalid providers registry: " + "; ".join(errors))
    return value


def cmd_providers(args):
    value = registry(); providers = value["providers"]
    if args.name:
        if args.name not in providers: raise SystemExit(f"unknown provider: {args.name}")
        providers = {args.name: providers[args.name]}
    print(json.dumps({"schema_version": value["schema_version"], "providers": providers}, ensure_ascii=False, indent=2))


def cmd_cost_record(args):
    validate_usage(registry(), args.provider, args.unit); root = topic_root(args.slug)
    event = record(root / "logs/costs.jsonl", {"provider": args.provider, "operation": args.operation, "quantity": args.quantity, "unit": args.unit, "cost_usd": args.cost_usd, "estimated": args.estimated, "run_id": args.run_id, "metadata": {"note": args.note} if args.note else {}})
    print(json.dumps(event, ensure_ascii=False, indent=2))


def cmd_cost_summary(args):
    print(json.dumps(summarize(topic_root(args.slug) / "logs/costs.jsonl", args.run_id), ensure_ascii=False, indent=2))


def cmd_workspace_check(args):
    result = inspect_workspace(topic_root(args.slug)); print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"] or (args.require_explicit and not result["explicit_version"]): raise SystemExit(1)


def cmd_workspace_migrate(args):
    root = topic_root(args.slug); result = apply_migration(root) if args.apply else plan_migration(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]: raise SystemExit(1)


def cmd_export(args):
    root = topic_root(args.slug); check = inspect_workspace(root)
    if not check["valid"]: raise SystemExit("invalid workspace: " + "; ".join(check["errors"]))
    output = Path(args.output) if args.output else REPO_ROOT / "dist" / f"{args.slug}.deep-research.zip"
    print(json.dumps(export_topic(root, output), ensure_ascii=False, indent=2))


def cmd_verify_package(args):
    result = verify_package(Path(args.package)); print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]: raise SystemExit(1)


def cmd_release_check(args):
    result = check_repo(REPO_ROOT); provider_errors = validate_providers(load_providers(PROVIDERS_FILE))
    result["errors"].extend(f"providers: {error}" for error in provider_errors); result["errors"] = sorted(set(result["errors"])); result["valid"] = not result["errors"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"] or (args.strict and result["warnings"]): raise SystemExit(1)


def parser():
    p = argparse.ArgumentParser(prog="releasectl"); sub = p.add_subparsers(dest="command", required=True)
    providers = sub.add_parser("providers"); providers.add_argument("--name"); providers.set_defaults(func=cmd_providers)
    record_cmd = sub.add_parser("cost-record"); record_cmd.add_argument("slug"); record_cmd.add_argument("--provider", required=True); record_cmd.add_argument("--operation", required=True); record_cmd.add_argument("--quantity", type=float, required=True); record_cmd.add_argument("--unit", required=True); record_cmd.add_argument("--cost-usd", type=float, required=True); record_cmd.add_argument("--run-id", required=True); record_cmd.add_argument("--estimated", action="store_true"); record_cmd.add_argument("--note"); record_cmd.set_defaults(func=cmd_cost_record)
    summary = sub.add_parser("cost-summary"); summary.add_argument("slug"); summary.add_argument("--run-id"); summary.set_defaults(func=cmd_cost_summary)
    check = sub.add_parser("workspace-check"); check.add_argument("slug"); check.add_argument("--require-explicit", action="store_true"); check.set_defaults(func=cmd_workspace_check)
    migrate = sub.add_parser("workspace-migrate"); migrate.add_argument("slug"); migrate.add_argument("--apply", action="store_true"); migrate.set_defaults(func=cmd_workspace_migrate)
    export = sub.add_parser("export-topic"); export.add_argument("slug"); export.add_argument("--output"); export.set_defaults(func=cmd_export)
    verify = sub.add_parser("verify-package"); verify.add_argument("--package", required=True); verify.set_defaults(func=cmd_verify_package)
    release = sub.add_parser("release-check"); release.add_argument("--strict", action="store_true"); release.set_defaults(func=cmd_release_check)
    return p


if __name__ == "__main__":
    args = parser().parse_args(); args.func(args)
