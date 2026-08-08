# Runtime commands

## User-directed coordinator

The main Codex session is the only coordinator. Run `research.py brief` before research to load the bounded reuse plan, then `research.py next` after lifecycle writes.

```bash
python "$SKILL/scripts/research.py" brief
python "$SKILL/scripts/research.py" next
```

After a Run is delivered, `next` returns `awaiting_user_research_request`. Present the report and `plans/research-backlog.json`, then stop. A new Run may start only after the user explicitly asks to continue, refresh, or investigate a selected gap.

## Versioned handoffs

```text
ResearcherAssignment v1 → topic_researcher → Worker Result v2
CriticAssignment v1 → research_critic → Critic Review v2
SynthesisAssignment v1 → research_synthesizer → SynthesisResult v2
```

ResearcherAssignment includes research mode, last-Run time anchor, existing Evidence, known source URLs, prior Queries, relevant Claims, and reuse rules. A lite/standard Worker may return explicit reused Evidence with zero tool usage; Deep may not.

Persist results internally:

```bash
python "$SKILL/scripts/researchctl.py" ingest-worker --file worker-result.json
python "$SKILL/scripts/researchctl.py" critic-save --file critic-review.json
python "$SKILL/scripts/agentctl.py" synthesis-save --file synthesis-result.json
```

SynthesisResult v2 is search-free and includes `knowledge_delta` plus at most five `next_research` items. Saving it writes the report, `memory/knowledge-deltas.jsonl`, `memory/current.md`, and `plans/research-backlog.json`.

## Multi-Run state

- A successful first Run sets `baseline_completed=true` independently of Reflection.
- `start --mode initial` becomes incremental after the baseline.
- Run usage resets at each start; lifetime usage remains diagnostic.
- Existing Claims, Evidence, source URLs, prior Queries, reports, audits, and knowledge deltas remain available.

## Public workflow

```bash
python "$SKILL/scripts/research.py" new "主题名称" --budget standard
cd "<printed workspace path>"
codex
python "$SKILL/scripts/research.py" plan --questions 5
python "$SKILL/scripts/research.py" start --mode initial
python "$SKILL/scripts/research.py" next
python "$SKILL/scripts/research.py" finish --status complete
python "$SKILL/scripts/research.py" validate
```

Finish complete only when `research.py next` returns `ready_to_finish`; otherwise resolve blockers or close partial/failed.
