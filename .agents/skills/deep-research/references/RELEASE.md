# Release readiness

Before tagging a release candidate:

```bash
python -m compileall -q .agents/skills/deep-research/scripts scripts
python -m pytest -q
python scripts/install_smoke_test.py
python scripts/smoke_test.py
python .agents/skills/deep-research/scripts/releasectl.py release-check --strict
```

CI runs unit tests and syntax checks on Python 3.11 and 3.12 across Ubuntu and Windows, then runs the installer, release checks, and end-to-end Smoke. The release check verifies required runtime/config files, Agent Skill frontmatter, the 500-line limit, project/skill version equality, TOML syntax, provider manifests, test and changelog presence, CI presence, and common secret patterns.

Manual release checklist:

1. confirm all GitHub checks pass;
2. inspect provider pricing links and authentication contracts;
3. run secret-pattern scanning on the complete release diff;
4. run the installer in an isolated home and confirm Doctor passes;
5. verify Format 1, Format 2, and unversioned workspaces are rejected without mutation;
6. verify an exported Format 3 topic archive twice and compare hashes;
7. confirm `CHANGELOG.md` and version metadata;
8. review and merge through a Pull Request;
9. create the tag/release only after explicit approval.

Release checks reduce mistakes but cannot prove semantic research correctness or eliminate every secret pattern.
