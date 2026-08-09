# Minimal Format 3 example

Create the workspace through the public command; do not hand-build or migrate it:

```bash
SKILL="$HOME/.agents/skills/deep-research"
python "$SKILL/scripts/research.py" new "海外 AI 短剧" --budget standard
python "$SKILL/scripts/research.py" plan "海外-ai-短剧" --questions 1
python "$SKILL/scripts/research.py" start "海外-ai-短剧" --mode baseline
python "$SKILL/scripts/research.py" next "海外-ai-短剧"
```

The generated `state.json` begins with the following lifecycle boundary (timestamps and slug vary):

```json
{
  "workspace_format_version": 3,
  "status": "new",
  "knowledge_status": "empty",
  "baseline_completed": false,
  "active_run_id": null,
  "active_run_scope": null,
  "usage": {"queries": 0, "pages": 0, "evidence_cards": 0},
  "lifetime_usage": {"queries": 0, "pages": 0, "evidence_cards": 0}
}
```

During a Run, `active_run_scope` freezes its mode, budget profile, Design hash, and every assigned question ID. A complete finish clears the active scope, marks the baseline complete, and preserves Claims, Evidence, Verification events, prior Queries, reports, and knowledge deltas.

After report delivery, stop. A later Run requires an explicit user request:

```bash
python "$SKILL/scripts/research.py" continue "海外-ai-短剧" --question "北美市场最近有哪些变化？"
```

`continue` archives the previous Design, creates one bounded incremental question, and starts a fresh Run atomically. Legacy or unversioned workspaces fail validation and remain untouched.
