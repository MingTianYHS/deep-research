# Compact report standard

The default report is a concise decision document, not a process transcript. Accepted Evidence Cards and stable `[[ev-ID]]` citations remain the source of truth.

## Required structure

1. **YAML Properties** — title, topic, report type, status, dates, confidence, and tags.
2. **核心结论** — direct answer, confidence, strongest evidence, decisive caveat, and change condition.
3. **调研范围与方法** — question, definitions, time/geography, exclusions, evidence cut-off, and material access limits.
4. **核心发现** — facts before interpretation, organized by research question.
5. **冲突、限制与未解决问题** — combine material contradiction, uncertainty, scope limits, and only the gaps that could change the decision.
6. **决策启示与建议** — separate inference from recommendation and include conditions, trade-offs, and exit thresholds.
7. **来源** — only cited, accepted Evidence IDs. Publisher metadata and quality diagnostics are generated from Evidence, not rewritten by the model.

## Writing rules

- Cite every material factual paragraph near the statement with `[[ev-ID]]`.
- Preserve dates, units, denominators, population, geography, and version.
- Do not combine Evidence Cards into a stronger claim than they support.
- Treat repeated coverage from one origin as one source.
- State material weakening evidence before confidence and recommendations.
- Remove all TODO/pending markers before completion.
- Do not add a duplicate Claim table or prose quality-score section.

## Quality checks

The report gate uses hard checks only: required sections, citation coverage, numeric citation coverage, valid citations, independent origins, high-risk citations, unfinished markers, and YAML frontmatter. It intentionally has no weighted aggregate score. Quote fidelity remains a separate audit.
