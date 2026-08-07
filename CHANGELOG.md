# Changelog

All notable changes to this project are documented here.

## Unreleased

### Lean runtime v2

- Replace lite/standard per-Claim coordinator loops with one deterministic, idempotent Claim sync grouped by research question.
- Skip the separate report scaffold turn for lite/standard and synthesize directly into the final report path.
- Reduce the report contract to six body sections and generate quality diagnostics outside model-authored prose.
- Replace the weighted report score with explicit hard gates while retaining citation, independence, risk, and quote-audit safeguards.
- Preserve the strict deep workflow and explicit Claim review.

### Lean review workflow

- Added profile-specific coordinator step budgets and consecutive action loop detection.
- Added optional single-coordinator leases for identified sessions.
- Deferred Reflection in lite/standard runs.
- Replaced the second post-synthesis Critic pass in lite/standard with a deterministic mechanical lineage audit.
- Bounded Critic re-reviews and targeted remediation by profile.
