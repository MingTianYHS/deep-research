# Version history

## Preserved autonomous-research snapshot

- Product version: `0.9.0rc3`
- Commit: `5ac0ab62d0e45d86e7aea471bf7566cbc30e46b4`
- Archive branch: `archive/v0.9.0rc3-autonomous-research`
- Preserved on: 2026-08-08
- Architecture: state-driven deep-research system with bounded Researchers, snapshot-bound Critic review, search-free synthesis, profile-specific audits, and persistent topic workspaces.

This snapshot was frozen before the breaking product transition from an autonomous research system toward a user-directed research assistant. The archive branch must remain unchanged so the previous behavior can be inspected or restored.

## Research-assistant transition

Target version: `1.0.0rc1`

The new direction keeps the evidence lineage and persistent topic workspace while changing the operating goal:

- never run an unbounded autonomous research loop;
- recall existing Claims, Evidence, source URLs, and prior queries before searching;
- reuse fresh evidence and refresh known URLs before broad discovery;
- research only uncovered, stale, contradictory, or explicitly requested gaps;
- update a bounded knowledge snapshot after each completed Run;
- produce a prioritized, bounded backlog of worthwhile follow-up research;
- wait for the user before starting another Run.
