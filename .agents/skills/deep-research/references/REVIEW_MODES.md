# Review modes

Review behavior follows the existing budget profile so no new topic schema is required.

## lite and standard

- Keep the pre-synthesis Critic review and existing targeted remediation contract.
- Replace the second post-synthesis Critic quote-audit pass with `qualityctl.py audit-mechanical`.
- The mechanical audit verifies citation existence, accepted Source Attempt lineage, frozen content hashes, and preservation of the Evidence quote. It records `verification_mode=mechanical_lineage` and never claims that source text was independently re-fetched.
- Defer post-run Reflection so it cannot block delivery or the next run.

These defaults remove two low-yield orchestration loops while preserving the current Claim/Evidence and synthesis snapshot boundaries.

## deep

The deep profile keeps the audit-grade workflow unchanged:

- Critic-reviewed snapshot before synthesis;
- independent final quote verification with exact/normalized matching;
- Critic-linked Reflection before another run.

Use deep for medical, legal, compliance, investment, academic-publication, or explicitly audit-grade work when independent quote re-fetching is required.

## Commands

Inside a topic workspace:

```bash
python ~/.agents/skills/deep-research/scripts/research.py next
```

For lite/standard, a completed report returns:

```bash
python ~/.agents/skills/deep-research/scripts/qualityctl.py audit-mechanical --report "<report>"
```

`audit-mechanical` is a provenance check, not an external semantic or quote-fidelity review. The generated audit file makes that distinction machine-readable.
