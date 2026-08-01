from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def load_registry(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def resolve(registry: dict[str, Any], capability: str) -> list[dict[str, Any]]:
    matches = []
    for name, config in registry.get("tools", {}).items():
        if config.get("enabled") and capability in config.get("capabilities", []):
            matches.append({"name": name, **config})
    return sorted(matches, key=lambda item: int(item.get("priority", 0)), reverse=True)


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors = []
    tools = registry.get("tools", {})
    if not tools:
        return ["registry has no tools"]
    for name, config in tools.items():
        if not isinstance(config.get("enabled"), bool):
            errors.append(f"{name}: enabled must be boolean")
        if not config.get("capabilities"):
            errors.append(f"{name}: capabilities must not be empty")
        priority = config.get("priority")
        if not isinstance(priority, int) or not 0 <= priority <= 100:
            errors.append(f"{name}: priority must be 0..100")
    return errors
