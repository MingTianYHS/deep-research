#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.io_utils import atomic_write_json
from lib.research_design import template, validate_design


def cmd_init(args):
    path = Path(args.output); atomic_write_json(path, template(args.title)); print(json.dumps({"output": str(path)}, indent=2))


def cmd_validate(args):
    result = validate_design(json.loads(Path(args.file).read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"] or (args.strict and result["warnings"]): raise SystemExit(1)


def parser():
    p = argparse.ArgumentParser(prog="designctl"); sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.add_argument("--title", required=True); init.add_argument("--output", required=True); init.set_defaults(func=cmd_init)
    validate = sub.add_parser("validate"); validate.add_argument("--file", required=True); validate.add_argument("--strict", action="store_true"); validate.set_defaults(func=cmd_validate)
    return p


if __name__ == "__main__":
    args = parser().parse_args(); args.func(args)
