from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

SEARCH_CAPABILITIES = {"web_search", "news_search", "semantic_search"}
FETCH_CAPABILITIES = {
    "fetch",
    "static_page",
    "content_fetch",
    "url_to_markdown",
    "extract",
    "scrape",
    "dynamic_page",
    "authenticated_page",
    "anti_bot_page",
    "browser_session",
    "interaction",
    "media",
}
COST_CLASSES = {"low", "medium", "high"}


def load_registry(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _order_key(capability: str) -> str | None:
    if capability in SEARCH_CAPABILITIES:
        return "search_order"
    if capability in FETCH_CAPABILITIES:
        return "fetch_order"
    return None


def resolve(registry: dict[str, Any], capability: str) -> list[dict[str, Any]]:
    matches = []
    for name, config in registry.get("tools", {}).items():
        if config.get("enabled") and capability in config.get("capabilities", []):
            matches.append({"name": name, **config})
    order_key = _order_key(capability)
    order = registry.get("defaults", {}).get(order_key, []) if order_key else []
    positions = {name: index for index, name in enumerate(order)}
    return sorted(
        matches,
        key=lambda item: (
            0 if item["name"] in positions else 1,
            positions.get(item["name"], 0),
            -int(item.get("priority", 0)),
            item["name"],
        ),
    )


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors = []
    defaults = registry.get("defaults", {})
    tools = registry.get("tools", {})
    if not tools:
        return ["registry has no tools"]
    max_fallbacks = defaults.get("max_fallbacks")
    if not isinstance(max_fallbacks, int) or isinstance(max_fallbacks, bool) or max_fallbacks < 0:
        errors.append("defaults.max_fallbacks must be a non-negative integer")
    for field in ("free_quota_only", "allow_paid_overage"):
        if not isinstance(defaults.get(field), bool):
            errors.append(f"defaults.{field} must be boolean")
    if defaults.get("free_quota_only") and defaults.get("allow_paid_overage"):
        errors.append("free_quota_only cannot allow paid overage")
    for name, config in tools.items():
        if not isinstance(config.get("enabled"), bool):
            errors.append(f"{name}: enabled must be boolean")
        if not config.get("kind"):
            errors.append(f"{name}: kind is required")
        capabilities = config.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            errors.append(f"{name}: capabilities must not be empty")
        elif len(capabilities) != len(set(capabilities)):
            errors.append(f"{name}: capabilities must not contain duplicates")
        priority = config.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool) or not 0 <= priority <= 100:
            errors.append(f"{name}: priority must be 0..100")
        if config.get("cost_class") not in COST_CLASSES:
            errors.append(f"{name}: cost_class must be one of {sorted(COST_CLASSES)}")
    for key in ("search_order", "fetch_order"):
        order = defaults.get(key)
        if not isinstance(order, list) or not order:
            errors.append(f"defaults.{key} must be a non-empty list")
            continue
        if len(order) != len(set(order)):
            errors.append(f"defaults.{key} must not contain duplicates")
        for name in order:
            if name not in tools:
                errors.append(f"defaults.{key} references unknown tool {name}")
            elif not tools[name].get("enabled"):
                errors.append(f"defaults.{key} references disabled tool {name}")
    return errors
