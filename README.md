# deep-research

A lightweight, persistent deep-research skill for OpenAI Codex.

**Release candidate:** `0.6.0rc1` · Python 3.11+

## Capabilities

- repository-scoped Codex skill and native parallel subagents
- pluggable host/MCP search and fetch routing
- persistent, versioned topic workspaces and optional topic-level agents
- hard Lite / Standard / Deep budgets and resumable runs
- Claim–Evidence event graph, citation checks, quality gates, and quote audits
- provider manifests and normalized actual/estimated cost events
- deterministic topic export packages and migration/release checks
- prompt-injection isolation and coordinator-only writes

## Quick start

```bash
CTL=.agents/skills/deep-research/scripts/researchctl.py
QCTL=.agents/skills/deep-research/scripts/qualityctl.py
RCTL=.agents/skills/deep-research/scripts/releasectl.py

python "$CTL" init-topic "AI short drama market" --install-agent
python "$CTL" plan ai-short-drama-market --questions 5
python "$CTL" run-start ai-short-drama-market --mode initial
python "$CTL" ingest-worker ai-short-drama-market --file examples/worker-result.json
```

Check or stamp the workspace format:

```bash
python "$RCTL" workspace-check ai-short-drama-market
python "$RCTL" workspace-migrate ai-short-drama-market --apply
```

Record provider cost without hard-coding prices:

```bash
python "$RCTL" providers --name exa
python "$RCTL" cost-record ai-short-drama-market \
  --provider exa --operation search --quantity 2 --unit request \
  --cost-usd 0.014 --run-id run-ID --estimated
```

Validate and export:

```bash
REPORT=workspace/topics/ai-short-drama-market/reports/YYYYMMDD-final.md
python "$CTL" verify-citations ai-short-drama-market --report "$REPORT"
python "$QCTL" quality-report ai-short-drama-market --require-gates
python "$QCTL" audit-init ai-short-drama-market --report "$REPORT"
python "$QCTL" audit-validate --audit "$REPORT.audit.json" --final
python "$RCTL" export-topic ai-short-drama-market
python "$RCTL" verify-package --package dist/ai-short-drama-market.deep-research.zip
```

Release validation:

```bash
python -m pytest -q
python scripts/smoke_test.py
python "$RCTL" release-check --strict
```

The standard-library control plane owns deterministic state, budgets, validation, accounting, packaging, migrations, and recovery. Codex owns planning, native subagents, host/MCP tools, semantic extraction, critique, and synthesis.
