#!/usr/bin/env python3
"""Guarded topic creation, naming validation, and report implementation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import researchctl
from lib.topic_context import resolve_topic
from lib.workspace_paths import (
    is_within,
    topic_directory_name,
    topic_title,
    validate_topic_naming,
)


def _fail_naming(
    title: str, directory_name: str, allow_language_mismatch: bool
) -> None:
    errors = validate_topic_naming(
        title,
        directory_name,
        allow_language_mismatch=allow_language_mismatch,
    )
    if errors:
        raise SystemExit("invalid topic naming: " + "; ".join(errors))


def naming_result(topic: str | None, allow_language_mismatch: bool) -> dict[str, Any]:
    try:
        root = resolve_topic(researchctl.WORKSPACE_ROOT, topic)
    except FileNotFoundError as exc:
        return {
            "valid": False,
            "topic": topic,
            "workspace": None,
            "errors": [str(exc)],
        }
    subject = topic_title(root, root.name)
    errors = validate_topic_naming(
        subject,
        root.name,
        allow_language_mismatch=allow_language_mismatch,
    )
    return {
        "valid": not errors,
        "topic": subject,
        "workspace": str(root),
        "errors": errors,
    }


def cmd_init(args: argparse.Namespace) -> None:
    directory_name = args.directory_name or topic_directory_name(args.title)
    _fail_naming(args.title, directory_name, args.allow_language_mismatch)
    researchctl.cmd_init(
        argparse.Namespace(
            title=args.title,
            slug=directory_name,
            budget=args.budget,
            force=args.force,
            install_agent=False,
            allow_language_mismatch=args.allow_language_mismatch,
        )
    )


def cmd_report(args: argparse.Namespace) -> None:
    try:
        root = resolve_topic(researchctl.WORKSPACE_ROOT, args.topic)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    allow_language_mismatch = getattr(args, "allow_language_mismatch", False)
    subject = topic_title(root, root.name)
    errors = validate_topic_naming(
        subject,
        root.name,
        allow_language_mismatch=allow_language_mismatch,
    )
    if errors:
        raise SystemExit("invalid topic naming: " + "; ".join(errors))
    if args.output:
        output = Path(args.output).expanduser()
        reports_root = root / "reports"
        if not is_within(reports_root, output):
            raise SystemExit(
                "report output must stay inside the canonical topic reports directory; "
                "use releasectl.py export-topic for external copies"
            )
    researchctl.cmd_report_init(
        argparse.Namespace(
            slug=str(root),
            type=args.type,
            title=args.title,
            output=args.output,
            allow_language_mismatch=allow_language_mismatch,
        )
    )


def cmd_validate(args: argparse.Namespace) -> None:
    result = naming_result(args.topic, args.allow_language_mismatch)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="topicctl",
        description="Internal guarded implementation; use research.py for user workflow.",
    )
    sub = value.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-topic")
    init.add_argument("title")
    init.add_argument("--directory-name")
    init.add_argument(
        "--budget", choices=["lite", "standard", "deep"], default="standard"
    )
    init.add_argument("--force", action="store_true")
    init.add_argument("--allow-language-mismatch", action="store_true")
    init.set_defaults(func=cmd_init)

    report = sub.add_parser("report-init")
    report.add_argument("topic", nargs="?")
    report.add_argument(
        "--type", choices=["initial", "update", "final"], default="initial"
    )
    report.add_argument("--title")
    report.add_argument("--output")
    report.add_argument("--allow-language-mismatch", action="store_true")
    report.set_defaults(func=cmd_report)

    validate = sub.add_parser("validate-naming")
    validate.add_argument("topic", nargs="?")
    validate.add_argument("--allow-language-mismatch", action="store_true")
    validate.set_defaults(func=cmd_validate)
    return value


if __name__ == "__main__":
    arguments = parser().parse_args()
    arguments.func(arguments)
