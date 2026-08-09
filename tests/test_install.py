import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("deep_research_installer", REPO_ROOT / "scripts/install.py")
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_installer_copies_skill_agents_and_runs_doctor(tmp_path):
    agents_home = tmp_path / ".agents"
    codex_home = tmp_path / ".codex"
    result = installer.install(REPO_ROOT, agents_home, codex_home)
    assert result["valid"]
    assert result["doctor"]["valid"]
    assert (agents_home / "skills/deep-research/SKILL.md").is_file()
    assert len(result["installed_agents"]) == 3
    for filename in installer.AGENT_FILES:
        assert (codex_home / "agents" / filename).is_file()


def test_installer_refuses_implicit_overwrite_and_supports_force(tmp_path):
    agents_home = tmp_path / ".agents"
    codex_home = tmp_path / ".codex"
    installer.install(REPO_ROOT, agents_home, codex_home)
    with pytest.raises(FileExistsError):
        installer.install(REPO_ROOT, agents_home, codex_home)
    assert installer.install(REPO_ROOT, agents_home, codex_home, force=True)["valid"]
