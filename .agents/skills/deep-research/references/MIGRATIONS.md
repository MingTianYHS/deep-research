# Workspace format migrations

The current workspace format is version 2. For backward compatibility, an unversioned workspace is interpreted as legacy version 1 and must be migrated before format-2-only behavior is required.

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
- legacy `AGENT.md` is preserved for manual review while `AGENTS.md` becomes authoritative;
- format 2 adds the persistent topic-expert coordinator, bounded `context.md`, canonical Research Design, and Critic-validated lessons;
- back up or export a workspace before a future destructive migration.

Missing version markers are assumed to be version 1 because existing public legacy workspaces use the version-1 Claim/Evidence structure. Migration to version 2 preserves those records and creates the new coordination/context files around them.
