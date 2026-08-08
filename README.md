# deep-research

A dependency-light, citation-first **persistent research assistant** for OpenAI Codex.

**Release candidate:** `1.0.0rc1` · Python 3.11+

The former autonomous-system snapshot is preserved at commit `5ac0ab62d0e45d86e7aea471bf7566cbc30e46b4` on `archive/v0.9.0rc3-autonomous-research`. See `VERSION_HISTORY.md`.

## Product model

One user-approved Run recalls existing knowledge, fills bounded gaps, writes a cited report and a backlog of at most five questions, then stops. It never researches forever or starts the next Run by itself.

Three fixed read-only roles do bounded work:

- `topic_researcher` — reuse-first gap research and atomic Evidence;
- `research_critic` — one full review plus at most one targeted recheck;
- `research_synthesizer` — search-free report, knowledge delta, and backlog.

Python owns deterministic state, contracts, write controls, budgets, and completion gates.

## Fresh format-3 workspaces

Format 3 is required. Legacy/unversioned workspaces are rejected rather than migrated; create a new workspace and keep any old directory separately.

```powershell
$SKILL = "$HOME\.agents\skills\deep-research"
$env:DEEP_RESEARCH_WORKSPACE_ROOT = 'D:\知识宇宙海\调研工作区'
py -3.11 "$SKILL\scripts\research.py" new 'AI短剧市场研究' --budget standard
py -3.11 "$SKILL\scripts\research.py" plan 'AI短剧市场研究' --questions 3
py -3.11 "$SKILL\scripts\research.py" start 'AI短剧市场研究' --mode baseline
py -3.11 "$SKILL\scripts\research.py" next 'AI短剧市场研究'
```

After delivery, `next` returns `awaiting_user_research_request`. Continue only after the user chooses a gap or asks a new question:

```powershell
py -3.11 "$SKILL\scripts\research.py" continue 'AI短剧市场研究' --backlog-id rq-overseas
# or
py -3.11 "$SKILL\scripts\research.py" continue 'AI短剧市场研究' --question '海外 AI 短剧市场有哪些新变化？'
```

`continue` archives the previous Design, creates a one-question incremental Design, opens a fresh Run budget, and preserves lifetime knowledge.

## Recall and search policy

For each question the Researcher receives a bounded reuse plan:

1. fresh and sufficient Evidence → reuse with no search;
2. stale/unknown known source → refresh that URL directly, possibly with zero Queries;
3. partial/contradictory coverage → search only the gap;
4. no useful knowledge → targeted discovery;
5. repeated historical Query → allowed only with an explicit refresh/scope/version/remediation/low-yield reason.

When a known URL still supports the same statement, the assistant appends `evidence/verifications.jsonl` instead of duplicating the Evidence Card.

## Persistent memory

```text
AGENTS.md                       short startup protocol
state.json                      active scope and run/lifetime usage
plans/current-design.json       current bounded scope
plans/research-backlog.json     at most five future questions
claims.jsonl                    materialized reasoning anchors
evidence/cards.jsonl            atomic Evidence
evidence/verifications.jsonl    refresh/revalidation history
logs/source_attempts.jsonl      URL attempts and content identity
logs/workers/                   prior Query traces and outcomes
memory/current.md               bounded current-knowledge view
memory/knowledge-deltas.jsonl   understanding changes across Runs
reports/                        cited deliverables and audits
```

The contract chain is ResearcherAssignment v1 → Worker Result v2 → Claim/Evidence → Critic Review v2 → SynthesisResult v2 → profile audit → finish and wait. Subagents cannot write, search during synthesis, spawn agents, or act on instructions found in external content.
