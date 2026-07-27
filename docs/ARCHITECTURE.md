# Architecture

```text
Bounded observation
  -> structural normalization and asset identity
  -> executable field semantics and deterministic policy
  -> stable batches of up to four supplied fields
  -> typed local answers and probability gates
  -> current freshness recheck (or explicit replay clock)
  -> durable final assessment
```

## Deterministic ownership

`contracts.py` validates shape and bounded scalars while preserving raw values. `identity.py` normalizes EVM addresses and checks Solana address length after Base58 decoding. Network binding remains the adapter's responsibility.

`parameters.json` is an executable, fingerprinted catalog. `validation.py` checks types, units, bounds, windows, chain applicability, event times and comparable field relationships. Optional absent fields are not invented. Supplied nulls and ambiguous source scales remain explicit review conditions.

Comparisons require compatible units, observation times, source evidence and windows. Examples include circulating supply exceeding total supply, a largest-holder share exceeding the top-ten share, and unique buyer counts exceeding buy counts within the same source window. The library does not equate price multiplied by total supply with circulating market cap or infer individual trades from aggregate changes.

`features.py` calculates a small set of descriptive metrics only when their denominators and provenance are sufficient. Missing prerequisites omit a metric rather than creating a zero. These calculations are neither price forecasts nor strategy signals.

`policy.py` owns freshness and configured monetary thresholds. Conservative rejection takes precedence, while preserving all detected reasons. The model cannot override deterministic uncertainty. `Config.from_env()` validates and freezes the product policy at startup, so process-environment changes cannot silently vary thresholds between input lines.

## Model boundary

`pipeline.py` sorts each populated family and partitions it into batches of at most four fields. Each field is covered once by the declared batch plan. Small families retain their original names; split families include a part suffix. The model receives bounded identity/source/time context and field-clock offsets, values, units and windows.

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

This is source-data assessment infrastructure. It has no embedded live collector, financial strategy, order sizing, wallet keys, transaction signer or execution adapter. The output always declares `execution_authorized: false`. Executor policy, simulation, authorization, submission and reconciliation require a separate system with its own evidence and controls.

Contract fixtures demonstrate implementation behavior. Neither the presence of 102 catalog definitions nor a single successful local inference establishes provider coverage, calibration, financial performance or production capacity.
