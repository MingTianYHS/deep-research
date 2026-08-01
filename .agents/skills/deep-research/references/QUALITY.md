# Research quality and quote fidelity

Quality scoring prioritizes review; it does not turn judgment into objective truth. The report exposes every dimension and weight.

## Quality report

```bash
python scripts/qualityctl.py quality-report topic --output workspace/topics/topic/reports/quality.json
python scripts/qualityctl.py quality-report topic --require-gates
```

Dimensions:

- authority: default by source type, overrideable per card;
- directness: quote/direct observation versus summary;
- independence: repeated sources from one origin are discounted;
- specificity: precise locator versus broad assertion;
- freshness: source-type-specific half-life.

High prompt-injection-risk cards are visible but excluded from aggregate quality scores.

Quality gates cover average card score, primary-source ratio, question coverage, and high-risk-card count. A failed gate is a review signal, not permission to invent evidence.

## Quote-fidelity audit

Structural citation checks prove that evidence IDs and required fields exist. Quote fidelity requires fetching the source and comparing the recorded quote/locator with observed text.

```bash
python scripts/qualityctl.py audit-init topic --report path/to/report.md
# A read-only Codex reviewer checks each generated item and updates status/metadata.
python scripts/qualityctl.py audit-validate --audit path/to/report.md.audit.json --final
```

A verified item must include `checked_at` and `checked_by`. Failed or unavailable items require a reason. Final reports require all cited items verified unless the user explicitly accepts unresolved citations.
