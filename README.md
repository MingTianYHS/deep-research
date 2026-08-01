# deep-research

A lightweight, persistent deep-research skill for OpenAI Codex.

## Capabilities

- Codex repository skill under `.agents/skills/deep-research/`
- bounded parallel research through Codex subagents
- pluggable search/fetch routing through TOML
- persistent topic workspaces and optional topic-level agents
- evidence cards, claims, reports, logs, and resumable state
- Lite / Standard / Deep research budgets
- prompt-injection isolation and citation-first reporting

## Quick start

```bash
python .agents/skills/deep-research/scripts/researchctl.py init-topic "AI short drama market" --install-agent
python .agents/skills/deep-research/scripts/researchctl.py plan ai-short-drama-market --questions 5
python .agents/skills/deep-research/scripts/researchctl.py status ai-short-drama-market
```

Start Codex from the repository root and invoke:

```text
$deep-research research the AI short drama market using the standard budget
```

The control plane uses Python's standard library. Codex itself handles planning, subagents, web/MCP tools, extraction, critique, and synthesis.
