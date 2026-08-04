# deep-research

A dependency-light, citation-first deep-research Skill for OpenAI Codex.

**Release candidate:** `0.9.0rc1` · Python 3.11+

## What it does

`deep-research` turns one complex question into one persistent, auditable topic workspace. Codex coordinates planning and writes; three fixed read-only roles perform bounded research, adversarial review, and evidence-grounded synthesis:

- `topic_researcher`
- `research_critic`
- `research_synthesizer`

The durable knowledge model is `Source Attempt → Evidence Card → Claim–Evidence`. Reports are time-point outputs. `context.md` is a bounded rebuildable cache, and `memory/lessons.jsonl` stores only Critic-validated research lessons.

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

`research.py` is the documented user-facing entry point. The `*ctl.py` scripts are the internal control plane used by the topic-expert coordinator and maintainers.

```powershell
$SKILL = "$HOME\.agents\skills\deep-research"
py -3.11 "$SKILL\scripts\research.py" new 'AI短剧市场研究' --budget standard
cd 'D:\知识宇宙海\调研工作区\AI短剧市场研究'
codex
```

Inside the topic directory:

```powershell
py -3.11 "$SKILL\scripts\research.py" plan --questions 5
py -3.11 "$SKILL\scripts\research.py" brief
py -3.11 "$SKILL\scripts\research.py" start --mode baseline
py -3.11 "$SKILL\scripts\research.py" status
py -3.11 "$SKILL\scripts\research.py" report --type initial
py -3.11 "$SKILL\scripts\research.py" finish --status complete
py -3.11 "$SKILL\scripts\research.py" validate
```

The public `new` command intentionally has no destructive `--force` option. Topic creation and report initialization always pass through the guarded implementation.

## Naming and workspace boundary

- One research topic has exactly one canonical writable workspace.
- Chinese topics use Chinese human-readable directories and report names by default.
- Stable Question, Evidence, Claim, Run, schema, and Agent identifiers remain ASCII.
- English product, project, protocol, and proper names remain unchanged when they are the natural name.
- Reports stay inside the canonical topic workspace. External copies use explicit export tooling.
- Do not initialize workspaces with `mkdir`, `New-Item`, or hand-written `topic.toml`/`state.json`.
- Do not represent one topic with a second directory, report copy, symlink, junction, or hard link.

Existing workspaces migrate to format 2 with:

```powershell
py -3.11 "$SKILL\scripts\releasectl.py" workspace-migrate <slug> --apply
```

## Research lifecycle

The coordinator executes the internal lifecycle behind the public workflow:

1. Create or synchronize the canonical Research Design.
2. Build a bounded baseline, incremental, or question Brief.
3. Start a Run and delegate non-overlapping questions to `topic_researcher`.
4. Validate Query → Source Attempt → Evidence lineage and ingest accepted Evidence.
5. Materialize Claim–Evidence relations and run `research_critic`.
6. Use `research_synthesizer` only after evidence and claim review.
7. Verify citations, quality gates, report rubric, and final Quote Audit.
8. Finish the Run and apply a Critic-linked Reflection.

Low-level commands such as Worker ingestion, Critic persistence, Quote Audit, and Reflection remain available to the coordinator, but they are not separate user products.

## Search policy

The default registry enables native web, Tavily, Exa, Jina, and Firecrawl without paid overage. Each query uses one provider. Queries follow a bounded ladder: discovery, authority targeting, exact verification, disconfirming search, and a material cross-language check. One low-yield strategy pivot is allowed; a second low-yield result stops the route and becomes an explicit Gap.

Search results and snippets are discovery aids, never Evidence. Credentials stay outside the repository and topic workspaces. The project remains standard-library based: no scheduler, daemon, LangGraph, memory service, vector database, or heavyweight provider SDK.
