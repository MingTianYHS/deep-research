from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .costs import UNITS


def load(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def validate(registry: dict[str, Any]) -> list[str]:
    errors = []
    if registry.get("schema_version") != 1:
        errors.append("providers schema_version must be 1")
    providers = registry.get("providers", {})
    if not providers:
        return errors + ["providers registry is empty"]
    for name, config in providers.items():
        if not config.get("kind"):
            errors.append(f"{name}: kind is required")
        if not config.get("capabilities"):
            errors.append(f"{name}: capabilities are required")
        units = set(config.get("usage_units", []))
        unsupported = units - UNITS
        if unsupported:
            errors.append(f"{name}: unsupported usage units {sorted(unsupported)}")
        if not config.get("authentication"):
            errors.append(f"{name}: authentication contract is required")
        if not config.get("cost_reporting"):
            errors.append(f"{name}: cost_reporting contract is required")
    return errors


def provider(registry: dict[str, Any], name: str) -> dict[str, Any]:
    config = registry.get("providers", {}).get(name)
    if not config:
        raise ValueError(f"unknown provider: {name}")
    return config


def validate_usage(registry: dict[str, Any], name: str, unit: str) -> None:
    config = provider(registry, name)
    if unit not in config.get("usage_units", []):
        raise ValueError(f"provider {name} does not declare usage unit {unit}")
