from __future__ import annotations

import os
import re
import tomllib
import unicodedata
from datetime import datetime
from pathlib import Path

WORKSPACE_ENV = "DEEP_RESEARCH_WORKSPACE_ROOT"
WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
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
