# Report standard

Reports contain:

1. executive conclusion;
2. scope, date window, and assumptions;
3. supported findings;
4. conflicting or weakening evidence;
5. new information in this run;
6. risks and uncertainty;
7. unresolved questions and next actions;
8. source list.

Citations appear near claims as `[[ev-ID]]` and must resolve to accepted evidence cards. Distinguish event, publication, and access dates. State unavailable sources, failed tools, budget stops, and single-source areas; never imply completeness.

Before presenting a final report:

1. run `researchctl.py verify-citations` for structural validity;
2. run `qualityctl.py quality-report --require-gates` and disclose failed gates;
3. create and complete a `qualityctl.py audit-init` quote-fidelity audit;
4. run `qualityctl.py audit-validate --final`.

Read `QUALITY.md` for scoring limits and audit rules.
