#!/usr/bin/env python3
"""Unified user-facing workflow entry point for the deep-research Skill.

Low-level controllers remain available to the coordinator and maintainers. This
module is the documented public path and deliberately routes topic/report writes
through topicctl so naming and workspace-boundary guards cannot be skipped.
"""
from __future__ import annotations

import argparse

import researchctl
import topicctl


def cmd_new(args: argparse.Namespace) -> None:
    topicctl.cmd_init(
        argparse.Namespace(
            title=args.title,
            directory_name=args.directory_name,
            budget=args.budget,
            force=False,
            allow_language_mismatch=args.allow_language_mismatch,
        )
    )


def cmd_plan(args: argparse.Namespace) -> None:
    researchctl.cmd_plan(
        argparse.Namespace(slug=args.topic, questions=args.questions, force=False)
    )


def cmd_brief(args: argparse.Namespace) -> None:
    researchctl.cmd_brief(
        argparse.Namespace(slug=args.topic, question=args.question, output=args.output)
    )


def cmd_start(args: argparse.Namespace) -> None:
    researchctl.cmd_run_start(argparse.Namespace(slug=args.topic, mode=args.mode))


def cmd_status(args: argparse.Namespace) -> None:
    researchctl.cmd_status(argparse.Namespace(slug=args.topic))


def cmd_report(args: argparse.Namespace) -> None:
    topicctl.cmd_report(
        argparse.Namespace(
            topic=args.topic,
            type=args.type,
            title=args.title,
            output=args.output,
        )
    )


def cmd_finish(args: argparse.Namespace) -> None:
    researchctl.cmd_run_finish(
        argparse.Namespace(slug=args.topic, status=args.status, note=args.note)
    )


def cmd_validate(args: argparse.Namespace) -> None:
    topicctl.cmd_validate(
        argparse.Namespace(topic=args.topic, allow_language_mismatch=False)
    )
    researchctl.cmd_validate(argparse.Namespace(slug=args.topic))


def _topic_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "topic",
        nargs="?",
        help="Topic directory/name. Omit when running inside a topic workspace.",
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="research",
        description="Safe public workflow for one persistent deep-research topic.",
    )
    sub = value.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="Create one canonical topic workspace.")
    new.add_argument("title")
    new.add_argument("--directory-name")
    new.add_argument("--budget", choices=["lite", "standard", "deep"], default="standard")
    new.add_argument("--allow-language-mismatch", action="store_true")
    new.set_defaults(func=cmd_new)

    plan = sub.add_parser("plan", help="Create or synchronize the canonical Research Design.")
    _topic_argument(plan)
    plan.add_argument("--questions", type=int, default=5, choices=range(1, 9))
    plan.set_defaults(func=cmd_plan)

    brief = sub.add_parser("brief", help="Build bounded context for the topic or one question.")
    _topic_argument(brief)
    brief.add_argument("--question")
    brief.add_argument("--output")
    brief.set_defaults(func=cmd_brief)

    start = sub.add_parser("start", help="Start a baseline, incremental, or deep-dive Run.")
    _topic_argument(start)
    start.add_argument(
        "--mode",
        choices=["baseline", "initial", "incremental", "deep-dive"],
        default="initial",
    )
    start.set_defaults(func=cmd_start)

    status = sub.add_parser("status", help="Show topic state and record counts.")
    _topic_argument(status)
    status.set_defaults(func=cmd_status)

    report = sub.add_parser("report", help="Create a report inside the canonical topic workspace.")
    _topic_argument(report)
    report.add_argument("--type", choices=["initial", "update", "final"], default="initial")
    report.add_argument("--title")
    report.add_argument("--output")
    report.set_defaults(func=cmd_report)

    finish = sub.add_parser("finish", help="Close the active Run after completion gates.")
    _topic_argument(finish)
    finish.add_argument("--status", choices=["complete", "partial", "failed"], default="complete")
    finish.add_argument("--note", default="")
    finish.set_defaults(func=cmd_finish)

    validate = sub.add_parser("validate", help="Validate naming, workspace, design, and records.")
    _topic_argument(validate)
    validate.set_defaults(func=cmd_validate)
    return value


if __name__ == "__main__":
    arguments = parser().parse_args()
    arguments.func(arguments)
