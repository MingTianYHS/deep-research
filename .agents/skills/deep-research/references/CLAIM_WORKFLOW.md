# Claim workflow

`claims.jsonl` is an append-only event log. Current claim state is materialized by replaying events.

## Create and link

```bash
python scripts/researchctl.py claim-create topic --text "Claim" --confidence 0.6 --core
python scripts/researchctl.py claim-link topic --claim cl-ID --evidence ev-ID --stance support --strength 0.8
```

Relations may support, contradict, or provide context. Re-linking the same evidence replaces the materialized relation instead of creating two active relations.

## Status changes

```bash
python scripts/researchctl.py claim-status topic --claim cl-ID --status supported --reason "two independent primary sources"
```

For a core claim, this records `claim.transition.proposed` and leaves current status unchanged. Human approval is explicit:

```bash
python scripts/researchctl.py claim-status topic --claim cl-ID --status supported --reason "reviewed" --approve-core
```

Allowed statuses: draft, supported, contested, rejected, unresolved.

## Citation markers

Reports cite evidence IDs as `[[ev-ID]]`. Structural verification confirms that every marker resolves to an accepted card with a URL, statement, and quote or locator. Network availability and quote fidelity remain semantic/tool-assisted checks performed by Codex.
