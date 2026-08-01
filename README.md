# deep-research

A lightweight, citation-first user-level deep-research Skill for OpenAI Codex.

**Release candidate:** `0.7.0rc1` · Python 3.11+

## What it optimizes

- decision-relevant question decomposition
- bounded, non-overlapping named Codex subagents
- expected-answer and disconfirming searches
- version-pinned technical research
- URL/content deduplication and HTTP error-page rejection
- atomic Evidence Cards and reviewed Claim–Evidence relations
- one adversarial critic pass and one targeted gap wave
- calibrated synthesis with conflict and uncertainty
- Obsidian-native reports with citation and quality gates
- Rollout diagnostics for custom-agent identity, final delivery, tool calls, failures, and cumulative Token counters

It intentionally has no scheduler, daemon, queue, vector database, or heavyweight agent framework.

## User-level installation only

Copy the complete Skill directory to:

```text
%USERPROFILE%\.agents\skills\deep-research
```

Copy the three named agents to:

```text
%USERPROFILE%\.codex\agents\topic-researcher.toml
%USERPROFILE%\.codex\agents\research-critic.toml
%USERPROFILE%\.codex\agents\research-synthesizer.toml
```

Project-level installation is not supported. Run the diagnostic after copying:

```powershell
py -3.11 "$HOME\.agents\skills\deep-research\scripts\runtimectl.py" doctor --strict
```

The coordinator must spawn the named agents. It must not silently replace a missing named agent with a generic child.

## Workspace location

Set `DEEP_RESEARCH_WORKSPACE_ROOT` to keep research data outside the user profile:

```powershell
$env:DEEP_RESEARCH_WORKSPACE_ROOT = 'D:\知识宇宙海\调研工作区'
[Environment]::SetEnvironmentVariable('DEEP_RESEARCH_WORKSPACE_ROOT', 'D:\知识宇宙海\调研工作区', 'User')
```

Reopen Codex or the terminal after the persistent setting. Codex must be allowed to read and write that directory. Chinese topic folders are supported. Reports use host-local `YYYYMMDD-主题.md`, `YYYYMMDD-主题-更新.md`, or `YYYYMMDD-主题-最终.md` names.

## Bounded research flow

```powershell
$SKILL = "$HOME\.agents\skills\deep-research"
py -3.11 "$SKILL\scripts\runtimectl.py" doctor --strict
py -3.11 "$SKILL\scripts\researchctl.py" init-topic 'AI短剧市场研究' --budget standard --install-agent
py -3.11 "$SKILL\scripts\designctl.py" init --title 'AI短剧市场研究' --output design.json
py -3.11 "$SKILL\scripts\designctl.py" validate --file design.json --strict
```

Codex then runs one named `topic_researcher` per validated question, validates every final worker object, runs one named `research_critic`, and synthesizes with the named `research_synthesizer`.

Validate a Worker result before ingestion:

```powershell
py -3.11 "$SKILL\scripts\runtimectl.py" validate-worker --file worker.json --profile standard --require-gates
```

A Worker must always return a final JSON object. A missing final result gets one recovery request; a second failure is recorded as failed rather than triggering unlimited search.

## Source and version controls

The runtime helper can reject 403/404/error pages and record normalized source attempts:

```powershell
py -3.11 "$SKILL\scripts\runtimectl.py" source-check --content-file page.txt --http-status 200 --url https://example.com/doc --tool docs --source-version v1 --log source-attempts.jsonl --require-eligible
```

For software/API/configuration research, identify the installed or requested version and prefer its matching tag or commit. Main-branch-only evidence must be disclosed as a version mismatch.

## Report quality

The Skill produces one Obsidian-native report format with YAML Properties, Chinese decision sections, native callouts, compact Claim–Evidence summaries, stable `[[ev-ID]]` citations, conflict/uncertainty treatment, and mechanical gates. No Dataview, Canvas, CSS snippet, or community plugin is required.

```powershell
py -3.11 "$SKILL\scripts\researchctl.py" verify-citations <slug> --report report.md
py -3.11 "$SKILL\scripts\qualityctl.py" quality-report <slug> --require-gates
py -3.11 "$SKILL\scripts\qualityctl.py" audit-init <slug> --report report.md
py -3.11 "$SKILL\scripts\qualityctl.py" audit-validate --audit report.md.audit.json --final
py -3.11 "$SKILL\scripts\evalctl.py" report-check <slug> --report report.md --require-gates
```

## Rollout audit

Exported Codex JSONL can be checked without modifying it:

```powershell
py -3.11 "$SKILL\scripts\runtimectl.py" rollout-audit --file rollout.jsonl --require-gates
```

The audit identifies generic workers, missing final messages, excessive or failed tool calls, duplicate URLs, context compactions, Guardian turns, and cumulative runtime Token counters. These diagnostics do not replace host billing data or factual review.

The standard-library control plane owns deterministic validation and persistence. Codex owns planning, tool use, evidence interpretation, critique, and synthesis.
