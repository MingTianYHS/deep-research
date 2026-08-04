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
python "$SKILL/scripts/research.py" validate
```

`report` creates a report target; it does not make a Run complete. Between `start` and `finish`, the topic-expert coordinator must execute the Research Design, persist current-Run Worker Results and accepted Evidence, review Claim–Evidence, save an approved Critic Review, write a substantive report, and pass citation, Evidence quality, report rubric, and final Quote Audit gates.

Only after those gates pass:

```bash
python "$SKILL/scripts/research.py" finish --status complete
```

Use `partial` or `failed` when completion evidence is unavailable. The public `new` command intentionally has no destructive `--force` option. Chinese topics use Chinese directories by default. An explicitly allowed language mismatch must repeat `--allow-language-mismatch` on later report and validation commands.

## Coordinator control plane

The main topic-expert session may use internal commands while executing the Skill contract:

```bash
python "$SKILL/scripts/researchctl.py" ingest-worker --file worker-result.json
python "$SKILL/scripts/researchctl.py" critic-save --file critic-review.json
python "$SKILL/scripts/researchctl.py" reflect --file reflection.json
python "$SKILL/scripts/qualityctl.py" quality-report --require-gates
python "$SKILL/scripts/evalctl.py" report-check --require-gates
```

`researchctl.py init-topic` and `researchctl.py report-init` are no longer exposed. User-visible topic and report writes go through `research.py` and the guarded implementation.

`brief` reuses the canonical Research Design, open questions, contested/unresolved Claims, known URLs, and active Lessons. `context.md` is a bounded cache, not evidence.

Worker ingestion requires Worker Result v2, a unique Worker ID, the exact active Run ID, and matching question, overlap, budget, and version boundaries. An approved Critic Review belongs to one active Run. A Reflection updates generation, bounded context, open questions, next actions, and validated Lessons, but never changes Claim status automatically.

Use `releasectl.py workspace-migrate <slug> --apply` only for workspace maintenance.
