# deep-research

A dependency-light, citation-first deep-research Skill for OpenAI Codex.

**Release candidate:** `0.9.0rc3` · Python 3.11+

## Architecture

The main Codex session is the only upper-level Agent orchestrator. Three fixed read-only roles perform bounded execution:

- `topic_researcher` — scoped search, Source Attempts, and atomic Evidence;
- `research_critic` — snapshot-bound adversarial review and targeted remediation;
- `research_synthesizer` — search-free synthesis of one approved snapshot.

Python provides deterministic state, versioned Agent contracts, write controls, and completion gates. It does not add another Agent runtime.

## Do subagents inherit the Skill?

Do not rely on it. A custom subagent may receive workspace context and host tools, but the parent Skill prompt and conversation are not a stable inheritance contract. `deep-research` therefore puts required search craft in `topic-researcher.toml` and sends a complete `ResearcherAssignment v1` containing scope, exclusions, known URLs, dependency results, disconfirming search, version anchors, and numeric limits.

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
py -3.11 "$SKILL\scripts\research.py" next
```

The coordinator calls `next` after each mutation and executes the returned action. Important phases include Research Design, Worker research, Claim review, Critic review, Critic remediation/recheck, report scaffold, search-free synthesis, Quote Audit, completion remediation, Run finish, and Reflection.

Low-level controls are internal:

```powershell
py -3.11 "$SKILL\scripts\researchctl.py" ingest-worker --file worker-result.json
py -3.11 "$SKILL\scripts\researchctl.py" critic-save --file critic-review.json
py -3.11 "$SKILL\scripts\agentctl.py" synthesis-save --file synthesis-result.json
```

## Contract chain

```text
ResearcherAssignment v1
→ Worker Result v2
→ Source Attempt
→ Evidence Card
→ Claim–Evidence
→ CriticAssignment v1
→ Critic Review v2 (snapshot-bound)
→ SynthesisAssignment v1
→ SynthesisResult v1 (search-free)
→ Report + Quote Audit
```

Any Design, Worker, Evidence, or Claim change invalidates the old Critic approval and forces `critic_recheck`. `changes_required` routes serious findings to bounded `topic_researcher` Targeted Search assignments before re-review.

## Naming and boundaries

- One topic has one canonical writable workspace.
- Chinese topics use Chinese human-readable directories and report names by default.
- Stable Question, Worker, Evidence, Claim, Finding, Review, Run, and schema IDs remain ASCII.
- Reports stay inside `<topic>/reports/`.
- Subagents remain read-only and never spawn other agents.
- Synthesizer never searches or introduces new Evidence.

## Search policy

Each query has one intent and one provider. Search results are discovery only. Researcher runs a disconfirming query, performs at most one strategy-changing low-yield pivot, and uses an initial known-URL attempt plus at most one failure-specific fallback. Free quotas only; no paid overage or key/account rotation.
