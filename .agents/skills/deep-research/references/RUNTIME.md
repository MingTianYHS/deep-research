# Runtime commands

## New topic

```bash
SKILL=~/.agents/skills/deep-research
python "$SKILL/scripts/researchctl.py" init-topic "Topic" --budget standard
cd "<printed workspace path>"
codex
```

## From inside a topic directory

```bash
python "$SKILL/scripts/researchctl.py" status
python "$SKILL/scripts/researchctl.py" plan --questions 5
python "$SKILL/scripts/researchctl.py" brief
python "$SKILL/scripts/researchctl.py" run-start --mode baseline
python "$SKILL/scripts/researchctl.py" ingest-worker --file worker-result.json
python "$SKILL/scripts/researchctl.py" run-finish --status complete
python "$SKILL/scripts/researchctl.py" reflect --file reflection.json
python "$SKILL/scripts/researchctl.py" validate
```

The slug remains accepted for remote operation. `brief` reuses current Research Design, open questions, contested/unresolved Claims, known URLs, and active Lessons. `context.md` is a bounded cache, not evidence.

A Reflection contains `run_id`, `summary`, `open_questions`, `next_actions`, and Critic-validated `lesson_candidates`. It increments `research_generation` but never changes Claim status automatically.

Use `releasectl.py workspace-migrate <slug> --apply` for workspace format 2.
