# Changelog

## 0.5.1

- Standardize public market and security source namespaces.
- Bind projected observations to archived source hashes and regenerate the verified casebook.
- Verify declared integer-to-boolean source transformations during export.

## 0.5.0

- Published the complete 15-minute market window with contract records, all native answers and per-network price results.
- Added an offline casebook verifier covering file integrity, native inputs, answer bindings and every exit-policy event.
- Moved report generation and its template into the installed package.
- Organized tests by contracts, strategy, runtime and reporting.
- Removed additional strategy inference from already-triggered TP/SL paths.
- Bound frozen report samples and native calls to their recorded evidence.


## 0.4.0

- Coverage-aware strategy decisions with configurable data requirements.
- Absent, null and chain-specific fields retained without unnecessary model calls.
- Entry and holding tasks use distinct data prerequisites.
- Detailed decision reasons with values, policy limits and source references.
- Archived security adapter, quote performance calculations and a local inspection report.
- Strategy schema v2, data policy v3 and parameter catalog v3.

The default policy accepts missing optional reports while enforcing known risk and invalid-data checks. Set the documented requirement flags when complete coverage is required. Orders remain external to the package.

## 0.3.0

- Position-aware SKIP, BUY, HOLD, HOLD_BAG, PROFIT, TP and SL decisions.
- Independent strategy policy for flow, concentration, exposure and exit thresholds.
- JEV/LAYA risk, flow and ownership assessments with typed answers.
- Source-bound account snapshots and durable strategy decision records.
- Strategy JSONL mode, policy inspection and position lifecycle documentation.

## 0.2.0

- Executable parameter catalog, explicit notes and bounded evidence context.
- Durable final assessments separate from the model cache.
- Short SQLite transactions with expiring inference claims and crash recovery.
- Stream boundaries preserve the next record and expose a byte offset for restart.
- Input failure fingerprints, complete HTTPS evidence references and offline catalog export.
- Versioned contract corpus, recovery regressions and Linux/Windows CI.
- Updated architecture, operations, API examples and source attribution.

## 0.1.0

- Versioned trading input and decision contracts.
- Local inference through a pinned Laya revision.
- Evidence-linked decisions, probability gates and persistent replay.
- Bounded JSONL processing with explicit per-record outcomes.
- Contract tests, package build and shared-runtime verification.
