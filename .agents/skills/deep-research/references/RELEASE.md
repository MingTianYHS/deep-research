# Release readiness

Before tagging a release candidate:

```bash
python -m pytest -q
python scripts/smoke_test.py
python .agents/skills/deep-research/scripts/releasectl.py release-check --strict
```

CI runs these checks on Python 3.11 and 3.12. The release check verifies required runtime/config files, Agent Skill frontmatter, the 500-line limit, project/skill version equality, TOML syntax, provider manifests, test and changelog presence, CI presence, and common secret patterns.

Manual release checklist:

1. confirm all GitHub checks pass;
2. inspect provider pricing links and authentication contracts;
3. run GitHub secret scanning on the release diff;
4. verify an exported topic archive twice and compare hashes;
5. review migration behavior against an exported legacy workspace;
6. confirm `CHANGELOG.md` and version metadata;
7. review and merge through a Pull Request;
8. create the tag/release only after explicit approval.

Release checks reduce mistakes but cannot prove semantic research correctness or eliminate every secret pattern.
