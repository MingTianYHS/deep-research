# deep-research

A lightweight, citation-first user-level deep-research Skill for OpenAI Codex.

**Release candidate:** `0.8.0rc1` · Python 3.11+

## Capabilities

- decision-relevant question decomposition and bounded named subagents
- expected-answer plus disconfirming search
- version-pinned technical research
- non-bypassable Worker and Source Attempt contracts
- URL/content deduplication and 401/403/404/error-page rejection
- optional `web-access` fallback for authorized login, dynamic, and anti-bot pages
- Evidence Cards, reviewed Claim–Evidence relations, adversarial critique
- Obsidian-native reports, quote audits, citation and quality gates
- Rollout diagnostics and Windows/Linux CI

No scheduler, daemon, queue, vector database, or heavyweight agent framework is used.

## User-level installation

```text
%USERPROFILE%\.agents\skills\deep-research
%USERPROFILE%\.codex\agents\topic-researcher.toml
%USERPROFILE%\.codex\agents\research-critic.toml
%USERPROFILE%\.codex\agents\research-synthesizer.toml
```

Optional browser fallback:

```text
%USERPROFILE%\.agents\skills\web-access
```

`web-access` requires its own Node/browser setup. It may use the user's existing browser login only for content the user is authorized to access. Deep research never extracts cookies/tokens, bypasses authorization, or performs account-changing actions.

```powershell
py -3.11 "$HOME\.agents\skills\deep-research\scripts\runtimectl.py" doctor --strict
$env:DEEP_RESEARCH_WORKSPACE_ROOT = 'D:\知识宇宙海\调研工作区'
```

## Flow

```powershell
$SKILL = "$HOME\.agents\skills\deep-research"
py -3.11 "$SKILL\scripts\researchctl.py" init-topic 'AI短剧市场研究' --budget standard --install-agent
py -3.11 "$SKILL\scripts\designctl.py" init --title 'AI短剧市场研究' --output design.json
py -3.11 "$SKILL\scripts\designctl.py" validate --file design.json --strict
py -3.11 "$SKILL\scripts\runtimectl.py" validate-worker --file worker.json --profile standard --require-gates
py -3.11 "$SKILL\scripts\researchctl.py" ingest-worker <slug> --file worker.json
```

`ingest-worker` repeats the complete Worker validation, so legacy or incomplete results cannot bypass the gate. It persists Source Attempts and complete Worker results before Evidence is used. Add `--rollout rollout.jsonl` to `validate-worker` when observed tool-call verification is available.

A failed static attempt may be followed once through the installed web-access Skill. The accepted browser extraction receives a distinct Source Attempt and content hash; the failed 401/403/404 attempt remains in the audit trail.

Reports use `YYYYMMDD-主题.md`, `YYYYMMDD-主题-更新.md`, or `YYYYMMDD-主题-最终.md`. Final validation requires nonzero valid citations, quality gates, and a Quote Audit containing observed text, match type, Source Attempt, and content hash.

The deterministic control plane owns validation and persistence. Codex owns planning, tool use, evidence interpretation, critique, and synthesis.
