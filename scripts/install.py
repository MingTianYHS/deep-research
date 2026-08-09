#!/usr/bin/env python3
"""Install the deep-research Skill and its three fixed Codex agents."""
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

SKILL_NAME = "deep-research"
AGENT_FILES = {
    "topic-researcher.toml": "topic_researcher",
    "research-critic.toml": "research_critic",
    "research-synthesizer.toml": "research_synthesizer",
}
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "scripts/research.py",
    "scripts/researchctl.py",
    "scripts/qualityctl.py",
    "config/budgets.toml",
    "config/orchestration.toml",
)


def default_agents_home() -> Path:
    return Path(os.environ.get("AGENTS_HOME", Path.home() / ".agents")).expanduser()


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def _targets(agents_home: Path, codex_home: Path) -> tuple[Path, Path]:
    return agents_home.expanduser().resolve() / "skills" / SKILL_NAME, codex_home.expanduser().resolve() / "agents"


def _agent_errors(path: Path, expected_name: str) -> list[str]:
    if not path.is_file():
        return [f"missing agent file: {path}"]
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"invalid agent TOML {path}: {exc}"]
    errors = []
    if value.get("name") != expected_name:
        errors.append(f"{path.name} name must be {expected_name}")
    if value.get("sandbox_mode") != "read-only":
        errors.append(f"{path.name} sandbox_mode must be read-only")
    if not str(value.get("developer_instructions") or "").strip():
        errors.append(f"{path.name} requires developer_instructions")
    return errors


def doctor(agents_home: Path, codex_home: Path) -> dict[str, Any]:
    skill, agent_dir = _targets(agents_home, codex_home)
    errors: list[str] = []
    warnings: list[str] = []
    if sys.version_info < (3, 11):
        errors.append("Python 3.11 or newer is required")
    for relative in REQUIRED_SKILL_FILES:
        if not (skill / relative).is_file():
            errors.append(f"missing skill file: {skill / relative}")
    for filename, expected_name in AGENT_FILES.items():
        errors.extend(_agent_errors(agent_dir / filename, expected_name))
    scripts = skill / "scripts"
    if scripts.is_dir():
        for path in sorted(scripts.rglob("*.py")):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError, UnicodeError) as exc:
                errors.append(f"invalid Python file {path}: {exc}")
    research = scripts / "research.py"
    if research.is_file() and not errors:
        completed = subprocess.run(
            [sys.executable, str(research), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            errors.append(f"research.py --help failed: {(completed.stderr or completed.stdout).strip()}")
    return {
        "valid": not errors,
        "skill": str(skill),
        "agents": str(agent_dir),
        "errors": errors,
        "warnings": warnings,
    }


def install(repo_root: Path, agents_home: Path, codex_home: Path, *, force: bool = False) -> dict[str, Any]:
    repo_root = repo_root.expanduser().resolve()
    source_skill = repo_root / ".agents" / "skills" / SKILL_NAME
    source_agents = repo_root / ".codex" / "agents"
    skill, agent_dir = _targets(agents_home, codex_home)
    missing = [str(source_skill / item) for item in REQUIRED_SKILL_FILES if not (source_skill / item).is_file()]
    missing.extend(str(source_agents / item) for item in AGENT_FILES if not (source_agents / item).is_file())
    if missing:
        raise FileNotFoundError("repository checkout is incomplete: " + ", ".join(missing))
    conflicts = [str(skill)] if skill.exists() else []
    conflicts.extend(str(agent_dir / item) for item in AGENT_FILES if (agent_dir / item).exists())
    if conflicts and not force:
        raise FileExistsError("installation targets already exist; rerun with --force to replace them: " + ", ".join(conflicts))
    if skill.exists():
        shutil.rmtree(skill)
    skill.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_skill, skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    agent_dir.mkdir(parents=True, exist_ok=True)
    for filename in AGENT_FILES:
        shutil.copy2(source_agents / filename, agent_dir / filename)
    diagnosis = doctor(agents_home, codex_home)
    if not diagnosis["valid"]:
        raise RuntimeError("post-install doctor failed: " + "; ".join(diagnosis["errors"]))
    return {
        "valid": True,
        "installed_skill": str(skill),
        "installed_agents": [str(agent_dir / item) for item in AGENT_FILES],
        "doctor": diagnosis,
    }


def _common_paths(command: argparse.ArgumentParser) -> None:
    command.add_argument("--agents-home", type=Path, default=default_agents_home())
    command.add_argument("--codex-home", type=Path, default=default_codex_home())


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="install", description="Install or diagnose the deep-research Codex Skill.")
    sub = value.add_subparsers(dest="command", required=True)
    install_cmd = sub.add_parser("install", help="Copy the Skill and three fixed agents to user-level homes.")
    _common_paths(install_cmd)
    install_cmd.add_argument("--force", action="store_true", help="Replace an existing installation.")
    doctor_cmd = sub.add_parser("doctor", help="Validate the installed Skill and agent files.")
    _common_paths(doctor_cmd)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            result = install(Path(__file__).resolve().parents[1], args.agents_home, args.codex_home, force=args.force)
        else:
            result = doctor(args.agents_home, args.codex_home)
    except (FileExistsError, FileNotFoundError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        result = {"valid": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
