# Release readiness

Before tagging a release:

```bash
python scripts/releasectl.py release-check --strict
```

The check verifies required skill/runtime/config files, Agent Skill frontmatter, the 500-line SKILL.md limit, TOML syntax, provider manifests, test and changelog presence, and common secret patterns in skill/agent files.

Manual release checklist:

1. run the Python test suite locally;
2. run the synthetic end-to-end fixture;
3. inspect provider pricing links and authentication contracts;
4. run GitHub secret scanning on the release diff;
5. verify an exported topic archive twice and compare hashes;
6. update `CHANGELOG.md` and version metadata;
7. review the final diff through a Pull Request;
8. create the tag/release only after explicit approval.

Release checks reduce mistakes but cannot prove semantic research correctness or eliminate every secret pattern.
