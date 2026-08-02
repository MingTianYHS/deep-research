# Runtime commands

The control plane does not call LLM/search providers. Use user-level paths.

```bash
SKILL=~/.agents/skills/deep-research
python "$SKILL/scripts/runtimectl.py" doctor --strict
python "$SKILL/scripts/researchctl.py" init-topic "Topic" --budget standard --install-agent
python "$SKILL/scripts/researchctl.py" plan topic --questions 5
python "$SKILL/scripts/researchctl.py" run-start topic --mode initial
python "$SKILL/scripts/runtimectl.py" validate-worker --file worker-result.json --profile standard --require-gates
python "$SKILL/scripts/researchctl.py" ingest-worker topic --file worker-result.json
python "$SKILL/scripts/researchctl.py" record-usage topic --queries 2 --pages 5 --input-tokens 8000 --output-tokens 1200
python "$SKILL/scripts/researchctl.py" run-finish topic --status complete
```

`ingest-worker` repeats validation and rejects a Worker result without accepted Source Attempts, complete Evidence Cards, budget use, and final status. Source Attempts are stored in `logs/source_attempts.jsonl`; complete Worker payloads are stored in `logs/workers/`.

Use `source-check --access-mode authenticated_browser` for content extracted through the optional web-access Skill. A failed static attempt and accepted browser attempt are separate records.

Only one topic mutation may hold the workspace lock. New workspaces are stamped with format version 1. Use `partial` when useful evidence exists but access, tools, or budget prevent completion.

Final reports require nonzero valid citations, source quality gates, report gates, and a Quote Audit with observed text, match type, accepted Source Attempt, and content hash.
