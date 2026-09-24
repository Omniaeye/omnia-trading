# Trading API

`process(event, ledger, backend, policy=Policy(), now=None)` returns
`omnia.trading.assessment.v1`. The backend is callable `(state, questions)` and
exposes `manifest()`. `now` supports deterministic caller-owned evaluation time.

An observation has exactly `id`, `source`, `observed_at`, `identity` and `fields`.
Identity contains `chain`, `network_id`, `contract`, `pool`. Supported chains are
robinhood, bsc and solana. `pool` can be null. Network identifiers are supplied by
the source adapter and kept separate, including test networks.

Each key in `fields` must exist in the [catalog](PARAMETERS.md). Each datapoint has:

| Field | Meaning |
| --- | --- |
| `value` | Finite scalar or null; strings and flags preserve source meaning |
| `unit` | Explicit unit; use USD only when verified by the source adapter |
| `window_seconds` | Explicit positive aggregation window or null when unknown |
| `observed_at` | Per-field source observation time with timezone |
| `evidence` | Opaque reference to the captured source evidence |

The output includes asset identity, complete observation hash, parameter count,
disposition, reason codes, per-group decision records and explicit group failures.
The original archive owns raw fields. `execution_authorized` is always false.
No transaction IDs are synthesized from aggregate counter differences.
