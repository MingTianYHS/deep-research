# Runtime commands

## Coordinator loop

The main Codex session is the only upper-level orchestrator. Run `research.py next` at session start and after every successful lifecycle write. Pass each returned versioned assignment unchanged to its named read-only Agent.

Custom subagents must not be assumed to inherit the parent Skill prompt or conversation. Required search craft and safety rules live in the Agent TOML plus the explicit assignment payload.

```bash
python "$SKILL/scripts/research.py" next
```

## Versioned handoffs

```text
ResearcherAssignment v1 → topic_researcher → Worker Result v2
CriticAssignment v1 → research_critic → Critic Review v2
SynthesisAssignment v1 → research_synthesizer → SynthesisResult v1
```

Persist results internally:

```bash
python "$SKILL/scripts/researchctl.py" ingest-worker --file worker-result.json
python "$SKILL/scripts/researchctl.py" critic-save --file critic-review.json
python "$SKILL/scripts/agentctl.py" synthesis-save --file synthesis-result.json
```

Critic Review v2 is bound to Design, current-run Worker, Evidence, and Claim hashes. Any change makes the approval stale and routes `research.py next` to `critic_recheck`. A current `changes_required` review routes up to three serious targeted searches to `topic_researcher` before recheck.

Synthesizer is search-free. Missing citations or Evidence return `partial` or `blocked`; the coordinator routes the gap back through Researcher, Claim review, and Critic. `agentctl.py synthesis-save` validates Run, Critic approval, snapshot, allowed Claim/Evidence IDs, output language, citations, and report path before writing.

## Public workflow

```bash
python "$SKILL/scripts/research.py" new "主题名称" --budget standard
cd "<printed workspace path>"
codex
python "$SKILL/scripts/research.py" next
python "$SKILL/scripts/research.py" plan --questions 5
python "$SKILL/scripts/research.py" start --mode baseline
python "$SKILL/scripts/research.py" report --type final
python "$SKILL/scripts/research.py" validate
```

Finish complete only when `research.py next` returns `ready_to_finish`; otherwise resolve the returned blockers or close partial/failed.
