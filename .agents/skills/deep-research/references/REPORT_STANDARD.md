# Report standard

A high-quality report contains:

1. **Executive conclusion** — direct answer, confidence, and the most decision-relevant caveat.
2. **Scope and method** — question, definitions, time window, geography, exclusions, search limits, and evidence cut-off.
3. **Findings by research question** — supported facts first, then interpretation.
4. **Conflicting or weakening evidence** — material disagreement, null findings, shared-source dependence, and plausible alternatives.
5. **Implications** — clearly labeled inference or recommendation; not presented as observed fact.
6. **Risks, uncertainty, and limitations** — what is unknown, single-source, inaccessible, stale, or method-sensitive.
7. **Unresolved questions and next actions** — only gaps that could materially change the conclusion.
8. **Sources** — accepted evidence references.
9. **Core claim–evidence table** — claim, epistemic type, supporting/contradicting evidence IDs, confidence, and caveat.

## Writing rules

- Cite near every material factual paragraph as `[[ev-ID]]`.
- Keep dates, units, denominators, population, and geography attached to numbers.
- Label observed fact, inference, causal interpretation, forecast, and recommendation when confusion is possible.
- Never turn correlation into causation, a forecast into fact, or absence of evidence into evidence of absence.
- Treat repeated coverage from one origin as one source.
- State unavailable sources, failed tools, budget stops, and single-source conclusions.
- Do not imply exhaustive search, objective certainty, or consensus unsupported by the evidence.

## Final checks

```bash
python researchctl.py verify-citations <slug> --report report.md
python qualityctl.py quality-report <slug> --require-gates
python qualityctl.py audit-init <slug> --report report.md
python qualityctl.py audit-validate --audit report.md.audit.json --final
python evalctl.py report-check <slug> --report report.md --require-gates
```

The report rubric checks mechanical completeness, citation coverage, quantitative citation coverage, independence, conflict treatment, uncertainty treatment, and citation validity. It does not prove factual correctness or causal validity.
