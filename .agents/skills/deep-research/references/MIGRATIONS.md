# Workspace format migrations

The current workspace format is version 1. For backward compatibility, an unversioned workspace is interpreted as legacy version 1. It can be explicitly stamped without rewriting research content.

```bash
python scripts/releasectl.py workspace-check topic
python scripts/releasectl.py workspace-migrate topic
python scripts/releasectl.py workspace-migrate topic --apply
python scripts/releasectl.py workspace-check topic --require-explicit
```

Rules:

- planning is read-only; mutation requires `--apply`;
- every applied migration appends `logs/migrations.jsonl`;
- migration writes use atomic replacement;
- a workspace newer than the runtime is rejected;
- raw evidence, claims, and citations are never silently rewritten;
- back up or export a workspace before a future destructive migration.

Version 0 to 1 formalizes the append-only evidence/claims contract. Missing version markers are assumed to be version 1 rather than version 0, because all existing public workspaces already use the version-1 structure.
