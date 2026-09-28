## Public source namespaces — 0.5.1

Public rank/security records use OMNIA namespaces. The casebook was regenerated
from source-verified captures and carries archived-event hashes before projection.
No raw capture was rewritten. Current tracked text has no legacy provider names.
155 tests, Ruff, runtime snapshot verification and the complete 757-file casebook
verification passed locally. Native model answers and price trajectories retained.

# OMNIA Trading

## Domain

- **Observation:** source values with units, windows, clocks and evidence references.
- **Data assessment:** structural and model checks producing candidate, review or skip.
- **Strategy decision:** SKIP, BUY, HOLD, HOLD_BAG, PROFIT, TP or SL bound to a position and policy.
- **Native assessment:** a recorded JEV/LAYA response to an exact typed request.
- **Price series:** captured quotes for one network, contract and pool.
- **Market window:** a fixed collection period with all included outcomes retained.
- **Casebook:** public observations, native assessments, trajectories and integrity manifest.
- **Exit-policy replay:** independent first-quote entry and calculated exits over recorded prices.

## Implementation

The library lives in `src/omnia_trading`. Reporting and casebook operations are
installed entry points; `tools/` contains maintenance tasks and compatibility
launchers. Tests are grouped by contracts, strategy, runtime and reporting.

Version 0.5.0 adds the 28 September market window and avoids extra strategy
inference when a validated held position already meets TP or SL. Data assessment
and freshness checks still apply. No wallet signing or execution adapter is included.

The recorded native cohort contains known risk-task disagreements. Preserve
those responses; new policy behavior cannot rewrite historical results.

Architecture decisions: `docs/adr/`. Technical map: `docs/ARCHITECTURE.md`.
