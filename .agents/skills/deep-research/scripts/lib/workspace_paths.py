from __future__ import annotations

import os
import re
import tomllib
import unicodedata
from datetime import datetime
from pathlib import Path

WORKSPACE_ENV = "DEEP_RESEARCH_WORKSPACE_ROOT"
WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
REPORT_SUFFIX = {"initial": "", "update": "-更新", "final": "-最终"}


def safe_component(value: str, fallback: str = "topic", limit: int = 80) -> str:
    """Return one UTF-8 path component that is safe on Windows, macOS, and Linux."""
    value = unicodedata.normalize("NFKC", str(value)).strip()
    value = WINDOWS_FORBIDDEN.sub("-", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value).strip(" .-")
    value = value[:limit].rstrip(" .-") or fallback
    if value.upper() in RESERVED_NAMES:
        value = f"_{value}"
    return value


def contains_cjk(value: str) -> bool:
    """Return whether a user-visible name contains CJK ideographs."""
    return bool(CJK_RE.search(unicodedata.normalize("NFKC", str(value))))


def topic_directory_name(title: str) -> str:
    """Derive the canonical human-readable topic directory from its title."""
    return safe_component(title)


def validate_topic_naming(title: str, directory_name: str, *, allow_language_mismatch: bool = False) -> list[str]:
    """Validate user-visible naming without restricting technical IDs or brand names."""
    errors: list[str] = []
    expected = topic_directory_name(title)
    actual = safe_component(directory_name)
    if actual != directory_name:
        errors.append(f"directory name is not portable: {directory_name!r}; use {actual!r}")
    if contains_cjk(title) and not contains_cjk(actual) and not allow_language_mismatch:
        errors.append(
            "Chinese topic titles must use a Chinese human-readable directory name; "
            f"use {expected!r} or pass --allow-language-mismatch explicitly"
        )
    return errors


def is_within(root: Path, candidate: Path) -> bool:
    """Return whether candidate resolves inside root (or equals it)."""
    root = root.expanduser().resolve()
    candidate = candidate.expanduser().resolve()
    return candidate == root or root in candidate.parents


def workspace_root(repo_root: Path) -> Path:
    configured = os.environ.get(WORKSPACE_ENV, "").strip()
    if configured:
        return Path(os.path.expandvars(configured)).expanduser()
    return repo_root / "workspace" / "topics"


def topic_title(root: Path, fallback: str) -> str:
    path = root / "topic.toml"
    if not path.exists():
        return fallback
    with path.open("rb") as handle:
        value = tomllib.load(handle).get("title")
    return str(value).strip() if value else fallback


def report_filename(title: str, report_type: str = "initial", now: datetime | None = None) -> str:
    moment = now or datetime.now().astimezone()
    return f"{moment.strftime('%Y%m%d')}-{safe_component(title)}{REPORT_SUFFIX.get(report_type, '')}.md"
