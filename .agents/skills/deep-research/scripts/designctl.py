#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from lib.io_utils import atomic_write_json
from lib.research_design import render_questions,template,validate_design

def cmd_init(a):
    value=template(a.title,a.questions,a.profile);path=Path(a.output);atomic_write_json(path,value)
    if a.questions_markdown:Path(a.questions_markdown).write_text(render_questions(value),encoding="utf-8")
    print(json.dumps({"output":str(path),"questions":a.questions},indent=2))
def cmd_validate(a):
    result=validate_design(json.loads(Path(a.file).read_text(encoding="utf-8")));print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result["valid"] or (a.strict and result["warnings"]):raise SystemExit(1)
def parser():
    p=argparse.ArgumentParser(prog="designctl");s=p.add_subparsers(dest="command",required=True)
    x=s.add_parser("init");x.add_argument("--title",required=True);x.add_argument("--output",required=True);x.add_argument("--questions",type=int,choices=range(1,9),default=1);x.add_argument("--profile",choices=["lite","standard","deep"],default="standard");x.add_argument("--questions-markdown");x.set_defaults(func=cmd_init)
    x=s.add_parser("validate");x.add_argument("--file",required=True);x.add_argument("--strict",action="store_true");x.set_defaults(func=cmd_validate);return p
if __name__=="__main__":a=parser().parse_args();a.func(a)
