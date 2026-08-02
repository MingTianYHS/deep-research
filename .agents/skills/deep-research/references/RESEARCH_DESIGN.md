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
- explicit exclusions;
- `target_version`, tag, commit, evidence date, or data vintage when behavior may change by release;
- the assigned worker budget and mandatory final-output reserve.

```bash
python ~/.agents/skills/deep-research/scripts/designctl.py init --title "Topic" --output design.json
python ~/.agents/skills/deep-research/scripts/designctl.py validate --file design.json --strict
```

## Decomposition rules

- Split by independently answerable uncertainty, not by website or keyword.
- Do not create separate questions whose expected evidence sets substantially overlap.
- Facts needed by comparison/causal questions become dependencies and run first.
- A forecast identifies base rate, mechanism, time horizon, and invalidating evidence.
- A causal question searches alternative explanations and distinguishes mechanism from correlation.
- A landscape question defines category boundaries before counting participants.
- A decision question defines criteria and trade-offs before comparing options.
- A software/configuration question pins the requested or installed version before interpreting source code.

Run only dependency-free questions in parallel. Five focused workers usually outperform eight overlapping workers. Spawn the named `topic_researcher`, not a generic subagent. The coordinator validates each final worker object, merges source clusters, and performs one named critic pass after the first wave.
