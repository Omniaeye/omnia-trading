# Validation

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
