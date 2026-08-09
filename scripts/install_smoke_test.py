#!/usr/bin/env python3
"""Exercise the user-level installer in an isolated temporary home."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run() -> dict:
    repo = Path(__file__).resolve().parents[1]
    installer = repo / "scripts" / "install.py"
    with tempfile.TemporaryDirectory(prefix="deep-research-install-") as directory:
        root = Path(directory)
        agents_home = root / ".agents"
        codex_home = root / ".codex"
        command = [sys.executable, str(installer), "install", "--agents-home", str(agents_home), "--codex-home", str(codex_home)]
        installed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        if installed.returncode != 0:
            raise RuntimeError(installed.stderr or installed.stdout)
        install_result = json.loads(installed.stdout)
        checked = subprocess.run(
            [sys.executable, str(installer), "doctor", "--agents-home", str(agents_home), "--codex-home", str(codex_home)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if checked.returncode != 0:
            raise RuntimeError(checked.stderr or checked.stdout)
        doctor_result = json.loads(checked.stdout)
        if not install_result.get("valid") or not doctor_result.get("valid"):
            raise RuntimeError("installer returned an invalid result")
        return {"valid": True, "installed_agents": len(install_result["installed_agents"]), "doctor": doctor_result}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
