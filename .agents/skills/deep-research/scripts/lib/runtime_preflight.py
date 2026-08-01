from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

AGENT_FILES = (
    "topic-researcher.toml",
    "research-critic.toml",
    "research-synthesizer.toml",
)
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "config/budgets.toml",
    "scripts/researchctl.py",
    "scripts/runtimectl.py",
)


def user_root(home: Path | None = None) -> Path:
    return (home or Path.home()).expanduser()


def codex_home(home: Path | None = None) -> Path:
    if home is None and os.environ.get("CODEX_HOME", "").strip():
        return Path(os.path.expandvars(os.environ["CODEX_HOME"])).expanduser()
    return user_root(home) / ".codex"


def expected_skill_dir(home: Path | None = None) -> Path:
    return user_root(home) / ".agents" / "skills" / "deep-research"


def expected_agent_dir(home: Path | None = None) -> Path:
    return codex_home(home) / "agents"


def _item(level: str, code: str, message: str, path: Path | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"level": level, "code": code, "message": message}
    if path is not None:
        item["path"] = str(path)
    return item


def diagnose(
    skill_dir: Path,
    workspace_root: Path,
    *,
    home: Path | None = None,
    python_version: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Diagnose the supported user-level installation without mutating it."""
    skill_dir = skill_dir.expanduser().resolve()
    workspace_root = workspace_root.expanduser()
    expected_skill = expected_skill_dir(home).resolve()
    agents = expected_agent_dir(home)
    version = python_version or (sys.version_info.major, sys.version_info.minor)
    checks: list[dict[str, Any]] = []

    if skill_dir == expected_skill:
        checks.append(_item("ok", "user_skill_layout", "User-level Skill location is active.", skill_dir))
    else:
        checks.append(_item("error", "skill_not_user_level", "Only the user-level Skill layout is supported.", expected_skill))

    if version >= (3, 11):
        checks.append(_item("ok", "python_version", f"Python {version[0]}.{version[1]} is supported."))
    else:
        checks.append(_item("error", "python_version", "Python 3.11 or newer is required."))

    for relative in REQUIRED_SKILL_FILES:
        path = skill_dir / relative
        checks.append(_item("ok" if path.is_file() else "error", "skill_file", f"Required Skill file: {relative}", path))

    for name in AGENT_FILES:
        path = agents / name
        checks.append(_item("ok" if path.is_file() else "error", "agent_file", f"Required custom agent: {name}", path))

    if workspace_root.exists() and workspace_root.is_dir():
        writable = os.access(workspace_root, os.W_OK)
        checks.append(_item("ok" if writable else "error", "workspace_writable", "Workspace directory is writable." if writable else "Workspace directory is not writable.", workspace_root))
    else:
        parent = workspace_root.parent
        creatable = parent.exists() and os.access(parent, os.W_OK)
        checks.append(_item("warning" if creatable else "error", "workspace_missing", "Workspace does not exist yet; it can be created." if creatable else "Workspace and its writable parent are missing.", workspace_root))

    global_agents = codex_home(home) / "AGENTS.md"
    if global_agents.is_file() and global_agents.stat().st_size > 20_000:
        checks.append(_item("warning", "large_global_instructions", "Global AGENTS.md exceeds 20 KB and may inflate every worker context.", global_agents))

    errors = [item for item in checks if item["level"] == "error"]
    warnings = [item for item in checks if item["level"] == "warning"]
    return {
        "valid": not errors,
        "installation_mode": "user-level",
        "skill_dir": str(skill_dir),
        "expected_skill_dir": str(expected_skill),
        "agent_dir": str(agents),
        "workspace_root": str(workspace_root),
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }
