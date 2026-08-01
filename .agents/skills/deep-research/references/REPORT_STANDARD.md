# Report standard

The Skill produces one Obsidian-native Markdown report format. This is a rendering and quality contract only: it does not change research design, Evidence Cards, Claim–Evidence relations, budgets, agents, migrations, or the JSONL source of truth.

The report must remain readable without Dataview, Canvas, CSS snippets, or community plugins. YAML Properties, wiki citations, and core Obsidian callouts are allowed; plugin-specific queries are not required.

## Quality construction order

A high-quality report is built in this order:

1. **Evidence readiness** — use only accepted Evidence Cards; preserve source origin, dates, units, denominator, population, geography, quote/locator, risk, and access limits.
2. **Claim readiness** — materialize reviewed claims and separate support, contradiction, and context. Do not draft a core conclusion from unreviewed evidence.
3. **Adversarial review** — resolve blocker/high critic findings or disclose them. Shared origins count as one source.
4. **Calibrated synthesis** — distinguish observation, inference, causal interpretation, forecast, and recommendation. State what would change the conclusion.
5. **Obsidian rendering** — add Properties, callouts, compact claim cards, source references, and a visible quality disclosure.
6. **Mechanical and human checks** — run citation, quality, quote-audit, and report gates. Failed gates must remain visible.

Presentation can make reasoning easier to inspect; it cannot repair weak evidence.

## Required report structure

1. **YAML Properties** — title, topic, report type, status, dates, confidence, and tags.
2. **核心结论** — direct answer, confidence, strongest evidence, most decision-relevant caveat, and change condition.
3. **调研范围与方法** — question, definitions, time window, geography, exclusions, search limits, evidence cut-off, unavailable sources, and failed tools.
4. **核心发现** — organized by research question; observed facts before interpretation.
5. **冲突与削弱性证据** — disagreement, null findings, shared-source dependence, method differences, and plausible alternatives.
6. **决策启示与建议** — inference and recommendation clearly separated from observation; include conditions, trade-offs, and exit thresholds.
7. **风险、不确定性与局限** — unknown, single-source, inaccessible, stale, scope-sensitive, or method-sensitive conclusions.
8. **未解决问题与后续行动** — only gaps that could materially change the decision, with required evidence and stopping conditions.
9. **核心主张与证据** — compact overview plus expandable claim cards containing support, contradiction, confidence, caveat, and change conditions.
10. **来源** — only cited, accepted evidence; include publisher, title, date, source type, and independence group.
11. **调研质量说明** — citation coverage, numeric coverage, independent origins, invalid/high-risk citations, conflict/uncertainty treatment, quote-audit status, and failed gates.

## Obsidian presentation rules

- Use YAML Properties for indexing, but keep substantive information in the report body.
- Use callouts only to improve scanning: `abstract` for conclusion, `warning` for the decisive caveat, `question` for conflict, `tip` for implications, `caution` for uncertainty, `todo` for high-value gaps, and `info` for quality disclosure.
- Keep citations as stable `[[ev-ID]]` tokens so the existing verifier, audit, and Claim–Evidence graph remain authoritative.
- Prefer a narrow claim summary table followed by expandable claim cards; do not use a six-column evidence table as the only explanation.
- Do not require Dataview, Canvas, custom CSS, or one-note-per-evidence storage.
- Do not use appearance as a substitute for evidence, contradiction, or uncertainty.

## Writing rules

- Cite every material factual paragraph near the supported statement as `[[ev-ID]]`.
- Keep dates, units, denominators, population, and geography attached to quantitative claims.
- Do not combine cards into a stronger claim than any cited evidence supports.
- Never turn correlation into causation, a forecast into fact, or absence of evidence into evidence of absence.
- Present material weakening evidence before confidence and recommendations.
- Treat repeated coverage from one original source as one independence group.
- State unavailable sources, failed tools, budget stops, and single-source conclusions.
- Remove all `TODO`, `待补充`, `待填写`, `待判定`, and `pending` markers before a report can pass final gates.
- Do not imply exhaustive search, objective certainty, or consensus unsupported by evidence.

## Final checks

```bash
python researchctl.py verify-citations <slug> --report report.md
python qualityctl.py quality-report <slug> --require-gates
python qualityctl.py audit-init <slug> --report report.md
python qualityctl.py audit-validate --audit report.md.audit.json --final
python evalctl.py report-check <slug> --report report.md --require-gates
```

The report rubric checks required and substantive sections, YAML Properties, unfinished markers, material citation coverage, quantitative citation coverage, source independence, conflict treatment, uncertainty treatment, and citation validity. It does not prove factual correctness, causal validity, or quote fidelity.
