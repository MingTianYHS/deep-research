# deep-research

A lightweight, persistent deep-research skill for OpenAI Codex.

## Capabilities

- Codex repository skill under `.agents/skills/deep-research/`
- bounded parallel research through Codex subagents
- pluggable search/fetch routing through TOML
- persistent topic workspaces and optional topic-level agents
- evidence cards, claims, reports, logs, and resumable run state
- atomic state writes and hard Lite / Standard / Deep budgets
- prompt-injection isolation and citation-first reporting

## Quick start

```bash
CTL=.agents/skills/deep-research/scripts/researchctl.py

python "$CTL" init-topic "AI short drama market" --install-agent
python "$CTL" plan ai-short-drama-market --questions 5
python "$CTL" run-start ai-short-drama-market --mode initial
python "$CTL" tools web_search --all
```

After Codex subagents return structured worker results:

```bash
python "$CTL" ingest-worker ai-short-drama-market --file worker-result.json
python "$CTL" record-usage ai-short-drama-market --queries 3 --pages 8 --input-tokens 12000 --output-tokens 1800
python "$CTL" validate ai-short-drama-market
python "$CTL" run-finish ai-short-drama-market --status complete --note "initial research"
```

Start Codex from the repository root and invoke:

```text
$deep-research research the AI short drama market using the standard budget
```

## Runtime boundary

The control plane uses Python's standard library and does not call model/search vendors directly. Codex handles planning, native subagents, host/MCP tools, semantic extraction, critique, and synthesis. The script owns deterministic state, evidence validation, deduplication, budgets, and run lifecycle.

See `.agents/skills/deep-research/references/RUNTIME.md` for commands and the worker-result contract.
