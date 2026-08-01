from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

REQUIRED_SKILL_FILES = ["SKILL.md", "config/tools.toml", "config/budgets.toml", "config/providers.toml", "config/source_policy.toml", "scripts/researchctl.py", "scripts/qualityctl.py"]
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{12,}"),
    re.compile(r"(?i)(?:api[_-]?key|secret|token)\s*[=:]\s*['\"]?[A-Za-z0-9_-]{16,}"),
]


def check_repo(repo_root: Path) -> dict[str, Any]:
    errors, warnings = [], []
    skill = repo_root / ".agents/skills/deep-research"
    for relative in REQUIRED_SKILL_FILES:
        if not (skill / relative).exists():
            errors.append(f"missing required skill file: {relative}")
    skill_md = skill / "SKILL.md"
    if skill_md.exists():
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\nname: deep-research\n" not in text or "\ndescription:" not in text:
            errors.append("SKILL.md frontmatter is invalid or incomplete")
        if len(text.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines")
    for config in (skill / "config").glob("*.toml"):
        try:
            with config.open("rb") as handle:
                tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"invalid TOML {config.name}: {exc}")
    scan_roots = [skill, repo_root / ".codex/agents"]
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".py", ".toml", ".json", ".jsonl"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f"possible secret in {path.relative_to(repo_root)}")
    if not (repo_root / "tests").exists():
        warnings.append("tests directory missing")
    if not (repo_root / "CHANGELOG.md").exists():
        warnings.append("CHANGELOG.md missing")
    return {"valid": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings))}
