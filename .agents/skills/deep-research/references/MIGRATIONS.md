# Workspace format policy

The current development workspace format is **3**.

Format 3 is a deliberate product boundary for the user-driven persistent research assistant. It adds immutable active-run scope, incremental continuation, bounded knowledge deltas and backlog, Evidence verification events, and run/lifetime usage separation.

## No legacy migration

Format 1, format 2, and unversioned workspaces are unsupported by this runtime. They are not rewritten or deleted. Create a fresh workspace instead:

```bash
python ~/.agents/skills/deep-research/scripts/research.py new "主题名称" --budget standard
```

Validation and release tooling report the old version and instruct the user to recreate the workspace. `workspace-migrate --apply` is intentionally a no-op for a valid format-3 workspace and refuses legacy formats.

This policy avoids expensive, ambiguous conversion of old Claims, Evidence, run state, and coordinator semantics. Preserve any old directory separately if historical records are needed; do not copy its mutable state into the new workspace automatically.
