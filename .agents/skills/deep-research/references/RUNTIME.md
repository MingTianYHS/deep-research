# Runtime commands

## User-directed coordinator

The main Codex session is the only coordinator. Run `research.py brief` before research to load bounded memory, then call `research.py next` after each lifecycle write.

```bash
python "$SKILL/scripts/research.py" brief
python "$SKILL/scripts/research.py" next
```

After a Run is delivered, `next` returns `awaiting_user_research_request`. Present the report and `plans/research-backlog.json`, then stop. A later Run may start only through `research.py continue` after the user explicitly selects a gap or asks a new question. Direct `start` cannot bypass this boundary after the baseline.

## Versioned handoffs

```text
ResearcherAssignment v2 → topic_researcher → Worker Result v2
CriticAssignment v2 → research_critic → Critic Review v2
SynthesisAssignment v1 → research_synthesizer → SynthesisResult v2
```

ResearcherAssignment v2 contains the question, scope, observable worker budgets, and a bounded `research_context`: mode, time anchor, selected Evidence, relevant Claims, known sources, and prior Queries. It omits the full workspace reuse plan and coordinator-only budgets. A Lite/Standard Worker may return explicit reused Evidence with zero tool usage; Deep may not.

CriticAssignment v2 mechanically identifies either `full_review` or `targeted_recheck`. A targeted recheck is restricted to the prior Finding IDs, cannot request new searches, and cannot open another review cycle.

Persist results internally:

```bash
python "$SKILL/scripts/researchctl.py" ingest-worker --file worker-result.json
python "$SKILL/scripts/researchctl.py" critic-save --file critic-review.json
python "$SKILL/scripts/agentctl.py" synthesis-save --file synthesis-result.json
```

SynthesisResult v2 is search-free and includes `knowledge_delta` plus at most five `next_research` items. Saving it writes the report, `memory/knowledge-deltas.jsonl`, `memory/current.md`, and `plans/research-backlog.json`.

## Multi-Run state

- A successful first Run sets `baseline_completed=true` independently of Reflection.
- Create the first Run with `start --mode baseline`.
- Create every later Run with explicit `continue --backlog-id ...` or `continue --question ...`.
- `continue` archives the old Design, creates one incremental question, and starts the fresh Run atomically.
- Run usage resets at each start; lifetime usage remains diagnostic.
- Existing Claims, Evidence, Verification events, source URLs, prior Queries, reports, audits, and knowledge deltas remain available.

## Public workflow

```bash
python "$SKILL/scripts/research.py" new "主题名称" --budget standard
cd "<printed workspace path>"
codex
python "$SKILL/scripts/research.py" plan --questions 3
python "$SKILL/scripts/research.py" start --mode baseline
python "$SKILL/scripts/research.py" next
# Execute only the returned bounded actions until ready_to_finish.
python "$SKILL/scripts/research.py" finish --status complete
python "$SKILL/scripts/research.py" validate
# Stop. Later, only after a user request:
python "$SKILL/scripts/research.py" continue --question "新的明确问题"
```

Finish complete only when `research.py next` returns `ready_to_finish`; otherwise resolve blockers or close partial/failed.
