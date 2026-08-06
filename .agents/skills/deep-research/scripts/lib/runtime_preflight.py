from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

AGENT_FILES = {
    "topic-researcher.toml": "topic_researcher",
    "research-critic.toml": "research_critic",
    "research-synthesizer.toml": "research_synthesizer",
}
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "config/budgets.toml",
    "config/tools.toml",
    "config/providers.toml",
    "config/source_policy.toml",
    "config/report_rubric.toml",
    "references/QUERY_CRAFT.md",
    "references/TOOL_ROUTING.md",
    "scripts/research.py",
    "scripts/researchctl.py",
    "scripts/topicctl.py",
    "scripts/agentctl.py",
    "scripts/runtimectl.py",
    "scripts/qualityctl.py",
    "scripts/evalctl.py",
    "scripts/releasectl.py",
    "scripts/designctl.py",
    "scripts/lib/workflow.py",
    "scripts/lib/agent_contracts.py",
    "scripts/lib/agent_snapshots.py",
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


def expected_web_access_dir(home: Path | None = None) -> Path:
    return user_root(home) / ".agents" / "skills" / "web-access"


def _item(
    level: str, code: str, message: str, path: Path | None = None
) -> dict[str, Any]:
    value: dict[str, Any] = {"level": level, "code": code, "message": message}
    if path is not None:
        value["path"] = str(path)
    return value


def _agent_check(path: Path, expected_name: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return [_item("error", "agent_file", f"Required custom agent: {path.name}", path)]
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [_item("error", "agent_toml", f"Invalid custom-agent TOML: {exc}", path)]
    missing = [
        key
        for key in ("name", "description", "developer_instructions")
        if not value.get(key)
    ]
    if missing:
        return [_item("error", "agent_contract", f"Agent missing fields: {missing}", path)]
    if value.get("name") != expected_name:
        return [_item("error", "agent_name", f"Expected agent name {expected_name}, got {value.get('name')}", path)]
    if value.get("sandbox_mode") != "read-only":
        return [_item("error", "agent_sandbox", "Research agents must use read-only sandbox mode.", path)]
    return [_item("ok", "agent_file", f"Validated custom agent: {expected_name}", path)]


def diagnose(
    skill_dir: Path,
    workspace_root: Path,
    *,
    home: Path | None = None,
    python_version: tuple[int, int] | None = None,
) -> dict[str, Any]:
    skill_dir = skill_dir.expanduser().resolve()
    workspace_root = workspace_root.expanduser()
    expected_skill = expected_skill_dir(home).resolve()
    agents = expected_agent_dir(home)
    version = python_version or (sys.version_info.major, sys.version_info.minor)
    checks: list[dict[str, Any]] = []
    checks.append(_item("ok" if skill_dir == expected_skill else "error", "user_skill_layout" if skill_dir == expected_skill else "skill_not_user_level", "User-level Skill location is active." if skill_dir == expected_skill else "Only the user-level Skill layout is supported.", skill_dir if skill_dir == expected_skill else expected_skill))
    checks.append(_item("ok" if version >= (3, 11) else "error", "python_version", f"Python {version[0]}.{version[1]} is supported." if version >= (3, 11) else "Python 3.11 or newer is required."))
    for relative in REQUIRED_SKILL_FILES:
        path = skill_dir / relative
        checks.append(_item("ok" if path.is_file() else "error", "skill_file", f"Required Skill file: {relative}", path))
    for filename, expected_name in AGENT_FILES.items():
        checks.extend(_agent_check(agents / filename, expected_name))
    if workspace_root.exists() and workspace_root.is_dir():
        probe = workspace_root / ".deep-research-write-probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            checks.append(_item("ok", "workspace_writable", "Workspace write probe succeeded.", workspace_root))
        except OSError as exc:
            checks.append(_item("error", "workspace_writable", f"Workspace write probe failed: {exc}", workspace_root))
    else:
        parent = workspace_root.parent
        creatable = parent.exists() and os.access(parent, os.W_OK)
        checks.append(_item("warning" if creatable else "error", "workspace_missing", "Workspace does not exist yet; it can be created." if creatable else "Workspace and its writable parent are missing.", workspace_root))
    web_access = expected_web_access_dir(home) / "SKILL.md"
    checks.append(_item("ok" if web_access.is_file() else "warning", "web_access", "web-access is available for authorized login/anti-bot fallback." if web_access.is_file() else "Optional web-access Skill not found; login/anti-bot pages may remain unavailable.", web_access))
    global_agents = codex_home(home) / "AGENTS.md"
    if global_agents.is_file() and global_agents.stat().st_size > 20_000:
        checks.append(_item("warning", "large_global_instructions", "Global AGENTS.md exceeds 20 KB and may inflate every worker context.", global_agents))
    errors = [item for item in checks if item["level"] == "error"]
    warnings = [item for item in checks if item["level"] == "warning"]
    return {"valid": not errors, "installation_mode": "user-level", "skill_dir": str(skill_dir), "expected_skill_dir": str(expected_skill), "agent_dir": str(agents), "workspace_root": str(workspace_root), "web_access_skill": str(web_access), "checks": checks, "error_count": len(errors), "warning_count": len(warnings)}
