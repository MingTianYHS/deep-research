# Runtime commands

## Public workflow

`research.py` is the single documented user-facing entry point. It routes topic creation and report initialization through the guarded naming and workspace-boundary implementation. Low-level `*ctl.py` commands are an internal control plane for the topic-expert coordinator and maintainers.

```bash
SKILL=~/.agents/skills/deep-research
python "$SKILL/scripts/research.py" new "主题名称" --budget standard
cd "<printed workspace path>"
codex
```

From inside a topic directory:

```bash
python "$SKILL/scripts/research.py" plan --questions 5
python "$SKILL/scripts/research.py" brief
python "$SKILL/scripts/research.py" start --mode baseline
python "$SKILL/scripts/research.py" status
python "$SKILL/scripts/research.py" report --type initial
python "$SKILL/scripts/research.py" finish --status complete
python "$SKILL/scripts/research.py" validate
```

The public `new` command intentionally has no destructive `--force` option. Chinese topics use Chinese human-readable directories by default. `report` rejects outputs outside the canonical topic workspace.

## Coordinator control plane

The main topic-expert session may use low-level commands while executing the Skill contract:

```bash
python "$SKILL/scripts/researchctl.py" ingest-worker --file worker-result.json
python "$SKILL/scripts/researchctl.py" critic-save --file critic-review.json
python "$SKILL/scripts/researchctl.py" reflect --file reflection.json
python "$SKILL/scripts/qualityctl.py" quality-report --require-gates
python "$SKILL/scripts/evalctl.py" report-check --require-gates
```

These are implementation controls, not separate user products. New user documentation must not instruct users to initialize topics or reports through `researchctl.py`.

`brief` reuses the canonical Research Design, open questions, contested/unresolved Claims, known URLs, and active Lessons. `context.md` is a bounded cache, not evidence.

New Worker ingestion requires `worker_result_version: 2`, a unique `worker_result_id`, and the exact active `run_id`. The Worker question, overlap key, budget profile, and version anchor are checked against `plans/current-design.json`. Worker-reported query/page usage and accepted Evidence are added exactly once because duplicate Worker IDs are rejected.

An approved Critic Review belongs to one active Run. `complete` requires Worker and Evidence from that Run, an approved Critic Review, live Evidence quality gates, and a citation-valid report that passes the report rubric and final source-identity-frozen Quote Audit. `partial` and `failed` may close without these completion gates.

A Reflection increments `research_generation` and updates bounded context and validated Lessons, but never changes Claim status automatically.

Use `releasectl.py workspace-migrate <slug> --apply` only for workspace maintenance and migration.
