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
python "$SKILL/scripts/researchctl.py" critic-save --file critic-review.json
python "$SKILL/scripts/researchctl.py" run-finish --status complete
python "$SKILL/scripts/researchctl.py" reflect --file reflection.json
python "$SKILL/scripts/researchctl.py" validate
```

The slug remains accepted for remote operation. `brief` reuses current Research Design, open questions, contested/unresolved Claims, known URLs, and active Lessons. `context.md` is a bounded cache, not evidence.

New Worker ingestion requires `worker_result_version: 2`, a unique `worker_result_id`, and the exact active `run_id`. The Worker question, overlap key, budget profile, and version anchor are checked against `plans/current-design.json`. Legacy Worker Result v1 remains readable by validation tools but cannot be persisted as new research output. Worker-reported query/page usage and accepted Evidence are added to the topic budget exactly once because duplicate Worker IDs are rejected.

An approved Critic Review is saved under `logs/critic_reviews/` and belongs to one active Run. `complete` requires a Worker and accepted Evidence from that Run, an approved Critic Review, live Evidence quality gates, and a citation-valid report that passes the report rubric and a final source-identity-frozen Quote Audit. `partial` and `failed` may still close without these completion gates.

A Reflection contains `run_id`, `critic_review_id`, `summary`, `open_questions`, `next_actions`, and Critic-validated `lesson_candidates`. The linked approved Critic Review must belong to the same Run. Reflection increments `research_generation` but never changes Claim status automatically.

Use `releasectl.py workspace-migrate <slug> --apply` for workspace format 2.
