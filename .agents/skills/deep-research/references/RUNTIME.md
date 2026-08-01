# Runtime commands

`researchctl.py` is the deterministic control plane and does not call LLM/search providers.

## Main lifecycle

```bash
python scripts/researchctl.py init-topic "Topic" --budget standard --install-agent
python scripts/researchctl.py plan topic --questions 5
python scripts/researchctl.py run-start topic --mode initial
python scripts/researchctl.py ingest-worker topic --file worker-result.json
python scripts/researchctl.py record-usage topic --queries 2 --pages 5 --input-tokens 8000 --output-tokens 1200
python scripts/researchctl.py run-finish topic --status complete
```

Only one active run is allowed. Use `partial` when useful evidence exists but a tool, source, or budget prevented completion.

## Claims and citations

See `CLAIM_WORKFLOW.md`. Typical sequence:

```bash
python scripts/researchctl.py claim-create topic --text "Claim" --core
python scripts/researchctl.py claim-link topic --claim cl-ID --evidence ev-ID --stance support --strength 0.8
python scripts/researchctl.py claim-status topic --claim cl-ID --status supported --reason "reviewed" --approve-core
python scripts/researchctl.py report-init topic --type initial
python scripts/researchctl.py verify-citations topic --report workspace/topics/topic/reports/YYYYMMDD-initial.md
```

## Incremental research

```bash
python scripts/researchctl.py incremental-plan topic
```

The generated plan uses `last_run_at`, open questions, contested/unresolved claims, pending core transitions, and known URLs. It instructs workers to exclude known sources unless verifying an update or contradiction.

## Tool resolution and validation

```bash
python scripts/researchctl.py tools web_search --all
python scripts/researchctl.py validate topic
```

Tool resolution is declarative and does not imply the provider is connected. Validation checks workspace files, evidence, claim events/relations, and tool registry configuration.
