# deep-research

A dependency-light, citation-first deep-research Skill for OpenAI Codex.

**Release candidate:** `0.9.0rc2` · Python 3.11+

## What it does

`deep-research` turns one complex question into one persistent, auditable topic workspace. The main Codex session is the upper-level Agent orchestrator; three fixed read-only roles perform bounded research, adversarial review, and evidence-grounded synthesis:

- `topic_researcher`
- `research_critic`
- `research_synthesizer`

Python does not replace the Codex orchestrator. It provides deterministic state, write controls, validation, and completion gates. The durable knowledge model is `Source Attempt → Evidence Card → Claim–Evidence`. Reports are time-point outputs. `context.md` is a bounded rebuildable cache, and `memory/lessons.jsonl` stores only Critic-validated research lessons.

## Install

```text
%USERPROFILE%\.agents\skills\deep-research
%USERPROFILE%\.codex\agents\topic-researcher.toml
%USERPROFILE%\.codex\agents\research-critic.toml
%USERPROFILE%\.codex\agents\research-synthesizer.toml
```

Optional: `%USERPROFILE%\.agents\skills\web-access`.

```powershell
py -3.11 "$HOME\.agents\skills\deep-research\scripts\runtimectl.py" doctor --strict
$env:DEEP_RESEARCH_WORKSPACE_ROOT = 'D:\知识宇宙海\调研工作区'
```

## One public workflow

`research.py` is the user-facing entry point. The `*ctl.py` scripts are internal coordinator and maintainer controls.

```powershell
$SKILL = "$HOME\.agents\skills\deep-research"
py -3.11 "$SKILL\scripts\research.py" new 'AI短剧市场研究' --budget standard
cd 'D:\知识宇宙海\调研工作区\AI短剧市场研究'
codex
```

Inside the topic directory:

```powershell
py -3.11 "$SKILL\scripts\research.py" next
py -3.11 "$SKILL\scripts\research.py" plan --questions 5
py -3.11 "$SKILL\scripts\research.py" brief
py -3.11 "$SKILL\scripts\research.py" start --mode baseline
py -3.11 "$SKILL\scripts\research.py" status
py -3.11 "$SKILL\scripts\research.py" report --type initial
py -3.11 "$SKILL\scripts\research.py" validate
```

`research.py next` derives the current workflow phase from persisted workspace state and returns one machine-readable coordinator contract. It may direct the main Codex session to create or repair a design, start a Run, delegate specific questions to `topic_researcher`, materialize Claim–Evidence, invoke `research_critic`, invoke `research_synthesizer`, verify a Quote Audit, resolve completion blockers, finish the Run, or apply Reflection.

The Codex coordinator should call `next` at session start and after every successful lifecycle write. It should execute the returned action itself and should not ask the user to run internal controllers. User input is reserved for material scope ambiguity and actions that genuinely need approval.

The topic-expert coordinator performs Worker research, Evidence ingestion, Claim review, Critic review, report writing, and all quality/audit gates between `start` and `finish`. `report` only creates the report target. It is not immediately followed by a successful complete finish.

After all current-Run completion gates pass and `next` returns `ready_to_finish`:

```powershell
py -3.11 "$SKILL\scripts\research.py" finish --status complete
```

## Naming and workspace boundary

- One topic has exactly one canonical writable workspace.
- Chinese topics use Chinese human-readable directories and report names by default.
- Stable Question, Evidence, Claim, Run, schema, and Agent identifiers remain ASCII.
- English product, project, protocol, and proper names remain unchanged when natural.
- Reports stay inside `<topic>/reports/`; explicit export tooling creates external copies.
- The public `new` command has no destructive `--force` option.
- `researchctl.py init-topic` and `researchctl.py report-init` are not exposed.
- Do not initialize workspaces with filesystem commands or hand-written state files.
- Do not represent one topic with a second directory, report copy, symlink, junction, or hard link.
- When a language mismatch is explicitly authorized at creation, repeat `--allow-language-mismatch` on report and validation commands.

Existing workspaces migrate with:

```powershell
py -3.11 "$SKILL\scripts\releasectl.py" workspace-migrate <slug> --apply
```

## Research lifecycle

1. Run `research.py next` to derive the legal phase and next coordinator action.
2. Create or synchronize the canonical Research Design.
3. Build a bounded baseline, incremental, or question Brief.
4. Start a Run and delegate the returned non-overlapping assignments to `topic_researcher`.
5. Validate Query → Source Attempt → Evidence lineage and ingest accepted Evidence.
6. Materialize Claim–Evidence relations and run `research_critic`.
7. Use `research_synthesizer` only after evidence and claim review.
8. Write the report and pass citations, Evidence quality, report rubric, and final Quote Audit.
9. Finish the Run and apply a Critic-linked Reflection.
10. Run `research.py next` after each mutation until the intended lifecycle stopping point.

Low-level Worker ingestion, Critic persistence, Quote Audit, and Reflection remain internal controls, not separate user products.

## Search policy

The default registry enables native web, Tavily, Exa, Jina, and Firecrawl without paid overage. Each query uses one provider. Queries follow a bounded ladder: discovery, authority targeting, exact verification, disconfirming search, and a material cross-language check. One low-yield strategy pivot is allowed; a second low-yield result stops the route and becomes an explicit Gap.

Search results and snippets are discovery aids, never Evidence. Credentials stay outside the repository and topic workspaces. The project remains standard-library based: no scheduler, daemon, LangGraph, memory service, vector database, or heavyweight provider SDK.
