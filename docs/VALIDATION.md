# Validation

## Version 0.2.0

Executed on Windows with Python 3.14.5. [Machine-readable receipt](verification-0.2.0.json)
binds the checks to source-file hashes and their actual verification time.

| Check | Result |
|---|---|
| Unit and integration suite | 62 tests passed |
| Input-boundary corpus | 400 cases exercised inside the suite |
| Ruff and diff whitespace checks | Passed |
| Shared product runtime fingerprints | Passed |
| Source distribution and wheel build | Passed |
| Clean-environment installed wheel imports and catalogs | Passed |
| Source distribution includes corpus, helpers and notices | Passed |

The case corpus is part of the reported suite, not 400 additional independent
model evaluations. Controlled backend responses exercise routing and failure
handling. No new model inference, throughput benchmark or accuracy measurement
was run for this release. The CI matrix additionally covers Python 3.10/3.12
on Windows and Linux; remote results belong to their exact commit.

Regression coverage includes source contract boundaries, final assessment storage,
claim recovery, cache reads during inference, durable failures and stream restart.
Product-specific assertions cover metadata policy and attribution in News, and
semantic domains, freshness rechecks, cross-field consistency and batch coverage
in Trading. Each package runs only its relevant product assertions.

## Evaluating model quality

Use separately reviewed examples and hold out time/source groups. Record the
checkpoint, task, catalog, policy and calibration versions. Report precision,
review coverage, false suppression, Brier/ECE and latency by task and language.
Neither contract-case counts nor repository history establish model quality.

## Historical 0.1.0 verification

The following receipt belongs to the previous release and is retained unchanged.
It does not validate the changed 0.2.0 pipeline.


Executed checks for the 0.1.0 product package. [Machine-readable receipt](verification.json).

| Check | Result |
| --- | --- |
| Contract and recovery tests | 42 passed |
| Ruff, compilation and shared-runtime fingerprint | Passed |
| Wheel build and isolated installed-package imports | Passed |
| Pinned Laya CPU inference | Completed on the included contract input |
| Durable replay | Cache hit for every recorded assessment |

## Inference result

The included observation received `usable` with probability 0.3855 for Market and 0.6475 for Risk. The configured 0.8 gate routed the assessment to `review`. The test clock was explicitly set to the example observation time; ordinary CLI replay also applies current-time freshness checks.

Cold processing, including model initialization, took 5.03 seconds.
Persistent replay took 0.005 seconds on this workstation.
These single-input measurements verify integration behavior. They are not throughput,
financial-performance, task-accuracy or production-capacity measurements.

The checkpoint reports a calibration warning for its 11-or-more-choice bucket.
These tasks use three choices; their active bucket passed the runtime check.
Answer probabilities still require task-specific calibration against independently reviewed data.

## Coverage

Tests exercise malformed input, identity, timestamps, unknown values, durable
replay, model failure, policy boundaries and recovery across records. Backend
doubles in contract tests provide controlled answers; the separate inference
receipt above uses the pinned local model.

For release decisions, measure accepted precision and review coverage on a labeled
source sample. Preserve source context and report results by platform and language.
