# Review modes

## Lite and standard

The bounded cycle is:

1. one full, snapshot-bound Critic review;
2. only the targeted remediation needed for blocker/high Findings;
3. at most one compact targeted recheck of the previous Finding IDs;
4. search-free synthesis;
5. deterministic mechanical lineage audit;
6. finish and wait for the user.

A targeted recheck cannot open new Findings or expand scope. If an allowed Finding remains unresolved after that recheck, return `review_budget_exhausted` and ask the user whether to finish partial. Post-run Reflection is optional and never blocks delivery or a later user-authorized continuation.

The mechanical audit verifies citation existence, accepted Source Attempt lineage, frozen content hashes, and preserved Evidence quotes. It does not independently re-fetch source text or prove factual truth.

## Deep

Deep retains the audit-grade path: fresh per-question verification and disconfirmation, up to four Critic reviews, bounded remediation, independent Quote Audit, and optional Critic-linked Reflection. It still completes one Run and waits; it never starts autonomous background research.

## Coordinator limits

`research.py next` consumes one atomic coordinator step while a Run is active. Current lifecycle/repeat limits are lite 25/2, standard 45/3, and deep 100/8. Exhaustion returns a user decision instead of continuing a loop. A short coordinator lease prevents two sessions from advancing the same Run concurrently.
