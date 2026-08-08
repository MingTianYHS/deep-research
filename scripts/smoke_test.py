#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
LIFECYCLE = ROOT / "scripts/lifecycle_smoke_test.py"


def main() -> None:
    """Exercise only a fresh format-3 workspace; legacy fixtures are unsupported."""
    subprocess.run([PYTHON, str(LIFECYCLE)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
