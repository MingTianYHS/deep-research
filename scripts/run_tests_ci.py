#!/usr/bin/env python3
from __future__ import annotations
import subprocess,sys

def escape(value:str)->str:
    return value.replace("%","%25").replace("\r","%0D").replace("\n","%0A")

result=subprocess.run([sys.executable,"-m","pytest","-q"],text=True,capture_output=True)
output=(result.stdout or "")+(result.stderr or "")
print(output,end="")
if result.returncode:
    print(f"::error title=pytest failure::{escape(output[-12000:])}")
raise SystemExit(result.returncode)
