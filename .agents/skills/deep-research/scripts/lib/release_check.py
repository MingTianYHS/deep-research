from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

REQUIRED_SKILL_FILES = [
    "SKILL.md",
    "config/tools.toml",
    "config/budgets.toml",
    "config/providers.toml",
    "config/source_policy.toml",
    "config/report_rubric.toml",
    "scripts/research.py",
    "scripts/researchctl.py",
    "scripts/topicctl.py",
    "scripts/qualityctl.py",
    "scripts/releasectl.py",
    "scripts/designctl.py",
    "scripts/evalctl.py",
    "scripts/runtimectl.py",
    "scripts/lib/workflow.py",
    "scripts/lib/workspace_paths.py",
    "scripts/lib/runtime_preflight.py",
    "scripts/lib/worker_contract.py",
    "scripts/lib/worker_context.py",
    "scripts/lib/critic_reviews.py",
    "scripts/lib/completion.py",
    "scripts/lib/source_attempts.py",
    "scripts/lib/rollout_audit.py",
    "references/RESEARCH_DESIGN.md",
    "references/QUERY_CRAFT.md",
    "references/TOOL_ROUTING.md",
]
REQUIRED_AGENTS = [
    "topic-researcher.toml",
    "research-critic.toml",
    "research-synthesizer.toml",
]
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{12,}"),
    re.compile(
        r"(?i)(?:api[_-]?key|secret|token)\s*[=:]\s*['\"]?[A-Za-z0-9_-]{16,}"
    ),
]


def project_version(repo_root: Path) -> str | None:
    try:
        with (repo_root / "pyproject.toml").open("rb") as handle:
            return tomllib.load(handle).get("project", {}).get("version")
    except (OSError, tomllib.TOMLDecodeError):
        return None


def skill_version(skill_md: str) -> str | None:
    match = re.search(r"(?m)^\s+version:\s*[\"']?([^\"'\s]+)", skill_md)
    return match.group(1) if match else None


def check_repo(repo_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    skill = repo_root / ".agents/skills/deep-research"
    agents = repo_root / ".codex/agents"
    for relative in REQUIRED_SKILL_FILES:
        if not (skill / relative).exists():
            errors.append(f"missing required skill file: {relative}")
    for name in REQUIRED_AGENTS:
        if not (agents / name).exists():
            errors.append(f"missing required agent file: {name}")

    skill_md = skill / "SKILL.md"
    skill_text = ""
    if skill_md.exists():
        skill_text = skill_md.read_text(encoding="utf-8")
        if (
            not skill_text.startswith("---\n")
            or "\nname: deep-research\n" not in skill_text
            or "\ndescription:" not in skill_text
        ):
            errors.append("SKILL.md frontmatter is invalid or incomplete")
        if len(skill_text.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines")

    project = project_version(repo_root)
    skill_release = skill_version(skill_text)
    if not project or not skill_release:
        errors.append("project and skill versions are required")
    elif project != skill_release:
        errors.append(f"version mismatch: project={project}, skill={skill_release}")

    for config in (skill / "config").glob("*.toml"):
        try:
            with config.open("rb") as handle:
                tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"invalid TOML {config.name}: {exc}")

    for scan_root in (skill, agents):
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix not in {
                ".md",
                ".py",
                ".toml",
                ".json",
                ".jsonl",
            }:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f"possible secret in {path.relative_to(repo_root)}")

    if not (repo_root / "tests").exists():
        warnings.append("tests directory missing")
    if not (repo_root / "CHANGELOG.md").exists():
        warnings.append("CHANGELOG.md missing")
    if not (repo_root / ".github/workflows/ci.yml").exists():
        warnings.append("CI workflow missing")
    if not (repo_root / "scripts/lifecycle_smoke_test.py").exists():
        warnings.append("lifecycle smoke test missing")
    return {
        "valid": not errors,
        "version": project,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
    }
