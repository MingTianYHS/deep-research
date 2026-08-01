from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.providers import load, validate, validate_usage


def test_provider_registry_is_valid():
    registry = load(SCRIPT_DIR.parent / "config/providers.toml")
    assert validate(registry) == []
    validate_usage(registry, "exa", "request")


def test_provider_rejects_undeclared_unit():
    registry = load(SCRIPT_DIR.parent / "config/providers.toml")
    try:
        validate_usage(registry, "github_mcp", "credit")
        assert False, "expected undeclared unit rejection"
    except ValueError:
        pass
