# deep-research

A dependency-light, citation-first **persistent research assistant** for OpenAI Codex.

**Release candidate:** `1.0.0rc1` · Python 3.11+

The preserved autonomous-system snapshot is commit `5ac0ab62d0e45d86e7aea471bf7566cbc30e46b4` on `archive/v0.9.0rc3-autonomous-research`. See `VERSION_HISTORY.md`.

## Product model

This project no longer aims to autonomously research forever. One user-approved Run recalls prior knowledge, fills bounded gaps, writes an auditable report and follow-up backlog, then stops.

Three fixed read-only roles perform bounded work:

- `topic_researcher` — reuse-first gap research, Source Attempts, and atomic Evidence;
- `research_critic` — one snapshot-bound review plus bounded remediation;
- `research_synthesizer` — search-free report, knowledge delta, and next-research backlog.

Python provides deterministic state, versioned contracts, write controls, budgets, and completion gates. It does not add another Agent runtime.

## Persistent topic memory

```text
AGENTS.md                       short operating protocol
state.json                      run state and run/lifetime usage
plans/current-design.json       current scoped questions
plans/research-backlog.json     at most five future questions
claims.jsonl                    materialized reasoning anchors
evidence/cards.jsonl            atomic accepted evidence
logs/source_attempts.jsonl      normalized URLs and content identity
logs/workers/                   prior query traces and outcomes
memory/current.md               bounded current knowledge view
memory/knowledge-deltas.jsonl   changes in understanding across Runs
reports/                        cited deliverables and audits
```

`AGENTS.md` tells the coordinator how to use memory; it does not contain growing research prose. Full web pages are not cached by default.

## Search decision

For each question the Researcher receives a bounded `reuse_plan`:

1. sufficient and fresh existing Evidence → reuse it with no search;
2. stale/unknown known source → refresh the URL directly;
3. uncovered or contradictory gap → perform targeted discovery;
4. repeated historical Query → allowed only with a recorded refresh/scope/version/remediation/low-yield reason.

Lite/standard can complete a question using explicit `reused_evidence_ids`. Deep always performs fresh per-question verification.

## Install

```text
%USERPROFILE%\.agents\skills\deep-research
%USERPROFILE%\.codex\agents\topic-researcher.toml
%USERPROFILE%\.codex\agents\research-critic.toml
%USERPROFILE%\.codex\agents\research-synthesizer.toml
```

```powershell
$SKILL = "$HOME\.agents\skills\deep-research"
py -3.11 "$SKILL\scripts\runtimectl.py" doctor --strict
$env:DEEP_RESEARCH_WORKSPACE_ROOT = 'D:\知识宇宙海\调研工作区'
```

## Public workflow

```powershell
py -3.11 "$SKILL\scripts\research.py" new 'AI短剧市场研究' --budget standard
cd 'D:\知识宇宙海\调研工作区\AI短剧市场研究'
codex
py -3.11 "$SKILL\scripts\research.py" brief
py -3.11 "$SKILL\scripts\research.py" next
```

After delivery, `next` returns `awaiting_user_research_request`. The coordinator presents the report and follow-up backlog and waits. A later explicit request such as “继续研究海外市场” starts an incremental Run with a fresh run budget while preserving lifetime knowledge.

## Contract chain

```text
ResearcherAssignment v1 (reuse plan)
→ Worker Result v2 (new and/or reused Evidence)
→ Claim–Evidence
→ Critic Review v2
→ SynthesisResult v2 (report + knowledge delta + backlog)
→ Profile audit
→ delivery and wait
```

Subagents remain read-only, the Synthesizer never searches, and external content is always untrusted data.
