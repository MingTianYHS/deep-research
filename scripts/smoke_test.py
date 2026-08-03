#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "workspace/topics/example-ai-research"
DIST = ROOT / "dist/smoke.deep-research.zip"
PYTHON = sys.executable
RESEARCH = ROOT / ".agents/skills/deep-research/scripts/researchctl.py"
QUALITY = ROOT / ".agents/skills/deep-research/scripts/qualityctl.py"
RELEASE = ROOT / ".agents/skills/deep-research/scripts/releasectl.py"
LIFECYCLE = ROOT / "scripts/lifecycle_smoke_test.py"


def run(*args: str) -> None:
    subprocess.run([PYTHON, *map(str, args)], cwd=ROOT, check=True)


def main() -> None:
    if TARGET.exists(): shutil.rmtree(TARGET)
    if DIST.exists(): DIST.unlink()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "examples/end-to-end", TARGET)
    try:
        run(RESEARCH, "validate", "example-ai-research")
        run(RESEARCH, "verify-citations", "example-ai-research", "--report", TARGET / "reports/initial.md")
        run(QUALITY, "quality-report", "example-ai-research", "--as-of", "2026-08-01", "--require-gates")
        run(QUALITY, "audit-init", "example-ai-research", "--report", TARGET / "reports/initial.md")
        run(RELEASE, "workspace-check", "example-ai-research", "--require-explicit")
        run(RELEASE, "export-topic", "example-ai-research", "--output", DIST)
        run(RELEASE, "verify-package", "--package", DIST)
    finally:
        if TARGET.exists(): shutil.rmtree(TARGET)
        if DIST.exists(): DIST.unlink()
    run(LIFECYCLE)


if __name__ == "__main__": main()
