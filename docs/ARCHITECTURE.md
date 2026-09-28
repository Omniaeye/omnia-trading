# Architecture

```text
Bounded observation
  -> structural normalization and asset identity
  -> executable field semantics and deterministic policy
  -> availability partition -> batches of up to four reported fields
  -> typed local answers and probability gates
  -> current freshness recheck (or explicit replay clock)
  -> durable final assessment
```

## Deterministic ownership

`contracts.py` validates shape and bounded scalars while preserving raw values. `identity.py` normalizes EVM addresses and checks Solana address length after Base58 decoding. Network binding remains the adapter's responsibility.

EVM token contracts remain 20-byte addresses. The identity's `pool` may be a
20-byte address or an opaque 32-byte pool identifier. The latter is not an
address and does not establish which protocol owns the pool. For example,
[Uniswap v4 defines PoolId as bytes32](https://github.com/Uniswap/v4-core/blob/main/src/types/PoolId.sol).

`parameters.json` is an executable, fingerprinted catalog. `validation.py` checks types, units, bounds, windows, chain applicability, event times and comparable field relationships. Optional absent fields are not invented. Supplied nulls are recorded as not reported; non-applicable fields are identified by chain. Reported ambiguous source scales remain review conditions.

Comparisons require compatible units, observation times, source evidence and windows. Examples include circulating supply exceeding total supply, a largest-holder share exceeding the top-ten share, and unique buyer counts exceeding buy counts within the same source window. The library does not equate price multiplied by total supply with circulating market cap or infer individual trades from aggregate changes.

`features.py` calculates a small set of descriptive metrics only when their denominators and provenance are sufficient. Missing prerequisites omit a metric rather than creating a zero. These calculations are neither price forecasts nor strategy signals.

`policy.py` owns freshness and configured monetary thresholds. Conservative rejection takes precedence, while preserving all detected reasons. The model cannot override deterministic uncertainty. `Config.from_env()` validates and freezes the product policy at startup, so process-environment changes cannot silently vary thresholds between input lines.

## Model boundary

### Independent strategy-fact validation

`strategy_facts.assess_facts()` validates recorded observations independently of
model inference. It retains every supplied field, separating eligible values
from quarantined values with explicit reasons. It uses the supplied capture
clock for replay and the current clock otherwise.

The result contains three checks:

| Check | Rule | Missing or ambiguous evidence |
|---|---|---|
| Risk | A valid rejecting report takes precedence; all four valid reports are required for `clear`. | `unknown` unless a valid rejecting report exists. |
| Flow | Compare buys and sells from the same capture, evidence and configured window. | `unknown`. |
| Ownership | Compare a validated top-ten share with the configured concentration limit. | `unknown`. |

Flow direction and entry eligibility are distinct. A 55/45 split is supportive
in direction, but does not meet a 60% entry threshold. Neither statement is a
prediction. Explicit percentage units can be normalized; unknown source scales
cannot. Zero total activity has no buy share.

This validation function makes no model calls, proposes no action, and is not
wired into `strategy.decide()`. Its results are intended for side-by-side
comparison before any change to the strategy's model gates. The existing model
answers, data-policy gates and seven-action strategy remain separate.

`tools/replay_strategy_facts.py` compares a frozen sample with expected labels
and previously recorded native answers. It matches observation IDs, records
input hashes, refuses to overwrite an output directory, and retains item errors.
Agreement with arithmetic rules is reported separately from native-model quality.

`pipeline.py` sorts each populated family and partitions it into batches of at most four fields. Each reported, applicable field is covered once by the declared batch plan. Other supplied fields are retained in unavailable_fields and the original observation fingerprint. Small families retain their original names; split families include a part suffix. The model receives bounded identity/source/time context and field-clock offsets, values, units and windows.

Every source string remains untrusted data. Typed questions ask about evidence quality, with closed choices `usable`, `inconsistent` and `insufficient`. A usable answer must also pass the configured maximum-answer-probability gate. This probability is distinct from the upstream entropy-based confidence and requires task-specific calibration.

The selected tokenizer checks instructions, options and complete input before inference. Partitioning reduces individual state size but does not guarantee that arbitrary source text fits. An oversized or failed batch is explicit; successful neighboring batches remain available. There is no silent truncation, omitted supplied field, or implied model comparison between separate batches.

## Time and replay

Freshness is evaluated before inference and again before the final realtime result is recorded. The assessment includes its start time, evaluation time and earliest expiry. Downstream consumers must recheck expiry after queueing or transport. Historical replay supplies an explicit aware `now`, recorded as replay mode rather than silently substituting current time.

Model-answer cache identity covers input, question/option order, checkpoint, runtime hashes, catalog fingerprint and policy configuration. It does not include the changing evaluation clock: the same evidence may reuse an answer while receiving a new policy disposition. The original model processing time remains intact.

The final product outcome is a separate durable record, including skips, reviews, backend failures and candidates. It carries the clock, policy, source references, batch coverage and final reasons necessary to distinguish those assessments. Source archives own raw observations; their complete normalized hash links them to the assessment.

## Runtime and recovery

`_engine` bundles the attributed OMNIA Laya integration with separately recorded product hardening hashes in the [runtime manifest](runtime-snapshot.json). The product can be installed independently of another checkout.

The SQLite ledger separates successful model decisions, final assessments, failure types and expiring inference claims. Cache reads do not require a write transaction. Short transactions coordinate ownership; model inference runs outside the write transaction. An expired owner cannot overwrite a replacement owner's result. A process failure can repeat model work after lease expiry, so inference is not promised to execute exactly once.

There is no embedded background scheduler or retry queue. The caller owns original input, process deadlines, retry backoff, partition ownership and storage retention. Separate ledger files do not provide distributed deduplication. See [Operations](OPERATIONS.md) for batch offsets and recovery behavior.

## Product boundary

The data pipeline feeds the position-aware strategy in strategy.py. strategy_contracts.py validates account snapshots and immutable policy limits; strategy_questions.py defines risk, flow and ownership tasks. The strategy records SKIP, BUY, HOLD, HOLD_BAG, PROFIT, TP and SL with proposed sizing and evidence.

Collection, wallet keys, transaction signing and execution remain external. Both data and strategy results declare execution_authorized: false. The execution adapter owns account serialization, capital reservations, quotes, submission and reconciliation. See [Strategy](STRATEGY.md) for rule precedence and position lifecycle.

Contract fixtures demonstrate implementation behavior. Neither the presence of 102 catalog definitions nor a single successful local inference establishes provider coverage, calibration, financial performance or production capacity.

## Reporting and published windows

`reporting.build()` owns archive validation, report assembly and the installed
HTML template. It verifies a frozen sample when supplied and binds native calls
to source fields and question hashes when recorded calls are available. The
`omnia-trading-report` command exposes it without checkout-specific imports.

`casebook.publish()` exports an immutable window to a new directory.
`casebook.verify()` checks published file hashes, the complete native cohort,
request/answer bindings, summary counts and every quote replay. No provider,
model or database is required to inspect a published window.

`tests/contracts`, `tests/strategy`, `tests/runtime` and `tests/reporting` test
these responsibilities separately. The shared `_engine` remains fingerprinted.
See [ADR 0001](adr/0001-capture-casebooks.md).

## Price-exit precedence

After data assessment and position guards pass, a reached TP/SL skips additional
strategy inference. The final clock and data policy are still rechecked before
recording the decision. `strategy_check_mode=price_exit` explains why no extra
risk/flow/ownership answers were requested. Other decisions use `coverage_gated`.
