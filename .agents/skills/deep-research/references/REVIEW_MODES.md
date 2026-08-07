# Review and orchestration modes

Review behavior follows the existing budget profile so no new topic schema is required.

## lite and standard

- Keep one pre-synthesis Critic review.
- Cap targeted remediation searches from `config/orchestration.toml`.
- Do not automatically run a second full Critic review after the profile limit is reached. Return `review_budget_exhausted` and ask whether to finish partial or explicitly upgrade to `deep`.
- Replace the second post-synthesis Critic quote-audit pass with `qualityctl.py audit-mechanical`.
- Defer post-run Reflection so it cannot block delivery or the next run.

The mechanical audit verifies citation existence, accepted Source Attempt lineage, frozen content hashes, and preservation of the Evidence quote. It records `verification_mode=mechanical_lineage` and never claims that source text was independently re-fetched.

## deep

The deep profile keeps the audit-grade workflow:

- up to four Critic reviews;
- up to three targeted searches per remediation dispatch;
- independent final quote verification with exact/normalized matching;
- Critic-linked Reflection before another run.

Use deep for medical, legal, compliance, investment, academic-publication, or explicitly audit-grade work when independent quote re-fetching is required.

## Coordinator hard limits

Every active-run `research.py next` call atomically consumes a coordinator step in `.runtime/coordinator-budget.json`.

Current limits:

- lite: 25 lifecycle steps, 2 consecutive repeats of one action;
- standard: 45 lifecycle steps, 3 consecutive repeats;
- deep: 100 lifecycle steps, 8 consecutive repeats.

When a limit is reached, the workflow returns `coordinator_budget_exhausted` instead of continuing an automatic LLM/Shell loop.

## Single-coordinator lease

`research.py next` acquires or refreshes `.runtime/coordinator-lease.json` when a stable coordinator identity is available. Identity resolution order is:

1. `--coordinator-id`;
2. `DEEP_RESEARCH_COORDINATOR_ID`;
3. `CODEX_THREAD_ID`;
4. `CODEX_SESSION_ID`.

Example:

```bash
python ~/.agents/skills/deep-research/scripts/research.py next \
  --coordinator-id "topic-session-2026-08-07"
```

A different coordinator is blocked until the 180-second lease expires. If no identity is available, `next` remains backward compatible but returns an explicit unenforced warning.

## Mechanical audit

Inside a lite/standard topic workspace:

```bash
python ~/.agents/skills/deep-research/scripts/qualityctl.py audit-mechanical \
  --report "<report>"
```

`audit-mechanical` is a provenance check, not an external semantic or quote-fidelity review. The generated audit file makes that distinction machine-readable.
