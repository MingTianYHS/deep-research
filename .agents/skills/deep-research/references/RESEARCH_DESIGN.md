# Research design and parallel decomposition

Deep research starts with a decision-relevant design, not a list of search queries.

Each question brief contains:

- `id` and one answerable `question`;
- `type`: fact, comparison, causal, forecast, decision, or landscape;
- `decision_relevance`;
- dependencies on earlier questions;
- a unique `overlap_key` defining the worker boundary;
- preferred source types;
- observable acceptance criteria;
- one `disconfirming_query`;
- alternative explanations for causal/forecast questions;
- explicit exclusions.

```bash
python scripts/designctl.py init --title "Topic" --output design.json
python scripts/designctl.py validate --file design.json --strict
```

## Decomposition rules

- Split by independently answerable uncertainty, not by website or keyword.
- Do not create separate questions whose expected evidence sets substantially overlap.
- Facts needed by comparison/causal questions become dependencies and run first.
- A forecast must identify base rate, mechanism, time horizon, and invalidating evidence.
- A causal question must search alternative explanations and distinguish mechanism from correlation.
- A landscape question must define category boundaries before counting participants.
- A decision question must define criteria and trade-offs before comparing options.

Run only dependency-free questions in parallel. Five focused workers usually outperform eight overlapping workers. The coordinator merges source clusters and performs one critic pass after the first wave.
