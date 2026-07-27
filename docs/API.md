# Trading API

## Input and responsibility

`process(event, ledger, backend, *, min_probability=.8, max_bytes=65536, policy=None, now=None)` returns `omnia.trading.assessment.v1` with an immutable `assessment_id`. `ledger` is a `DecisionLedger` with `decide()` and `record_assessment()`; `backend` exposes `manifest()` and is callable as `(state, questions)`.

An observation has exactly `id`, `source`, `observed_at`, `identity` and `fields`. Identity has exactly `chain`, `network_id`, `contract` and `pool`. Supported chain names are `robinhood`, `bsc` and `solana`; `pool` may be null. The source adapter binds network IDs, contracts, currencies and evidence to their actual source. Syntax validation is not an on-chain lookup.

Each field key must be in the [catalog](PARAMETERS.md), and each datapoint has exactly:

| Member | Contract |
| --- | --- |
| `value` | Finite JSON scalar or null; no nested structures |
| `unit` | Nonempty explicit unit, checked against the field definition |
| `window_seconds` | Integer 1–2,592,000 for an aggregate, or null for a snapshot/unknown window |
| `observed_at` | Source observation time with timezone |
| `evidence` | Opaque source-archive reference, 1–512 characters |

For example, a count over a confirmed one-minute window is:

```json
{
  "value": 180,
  "unit": "count",
  "window_seconds": 60,
  "observed_at": "2026-09-25T12:00:00Z",
  "evidence": "archive:observation-123"
}
```

`id` and `source` are bounded to 200 characters; text values to 2,048; units to 64. Unknown keys, malformed envelopes, invalid identity/address syntax, invalid metadata shape, nonfinite values and oversized packets raise a contract error. The CLI records those failures and continues within its batch limit.

Semantically questionable but structurally valid input is retained: null values, negative counts, mismatched units, invalid field-address syntax, wrong chain applicability, ambiguous timestamps and inconsistent windows become review reasons. Input is not silently rewritten. Optional absent fields are allowed; a supplied null is explicitly unknown and requires review.

## Executable semantics

Inspect the versioned catalog without a model or checkpoint:

```bash
omnia-trading --catalog
```

The JSON contains the catalog schema, SHA-256 and all definitions. `kind`, `allowed_units`, `minimum`, `maximum`, `requires_window`, `window_seconds` and `chains` drive deterministic validation. `description`, `note` and `missing_rule` describe source meaning and limits. `unit` remains a display hint; the normative accepted spellings are in `allowed_units`.

Counts reject booleans and fractional values. Proportion bounds use ratios: `50 percent` and `0.5 ratio` have equivalent declared magnitude; an unverified `source_scale` is not converted. Monetary policy requires exact `USD`, not an inferred quote currency. UTC event values require timezone-aware text; numeric epochs require `unix_seconds` or `unix_milliseconds`. Zero does not mean a valid event in January 1970.

A known 24-hour field requires `window_seconds: 86400`; unknown rolling windows require review. Snapshot fields require null windows. A field observed more than five seconds after its enclosing source observation is inconsistent. Event times more than five seconds after the corresponding field observation are also inconsistent. These tolerances do not establish source-clock accuracy.

Direct contract inspection is available independently of inference:

```python
from omnia_trading.contracts import normalize
from omnia_trading.validation import validate_semantics

item = normalize(observation)
reasons = validate_semantics(item)
```

This validates source semantics, not policy thresholds or current freshness. Those belong to `process()` / `policy.evaluate()`.

## Policy and clocks

`Policy()` defaults to `max_age_seconds=120`, `min_market_cap_usd=30000`, and `min_liquidity_usd=10000`. The required policy inputs are `market_cap`, `liquidity` and an explicit `is_honeypot` boolean. Missing required inputs require review. Supplied optional fields must also be semantically valid.

A well-formed below-threshold market value or a reported honeypot produces conservative `skip`. Rejection takes precedence over review, but stale, missing and inconsistent reasons are retained. No model is called for a deterministic skip. All other observations assess every supplied batch; an accepted model answer cannot erase a deterministic review reason.

With `now=None`, the library checks current UTC freshness before inference and again when constructing the final assessment. `evaluated_at` records the final check; `valid_until` is the earliest source observation time plus the configured maximum age. Consumers must check expiry themselves because storage, queues and transport can add delay.

An explicit timezone-aware `now` selects historical replay. The clock is fixed for both checks and recorded as `clock_mode: replay`. Replay is not evidence that a historical input is currently fresh:

```python
from datetime import datetime, timezone
from omnia_trading.pipeline import process

result = process(observation, ledger, backend,
                 now=datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
```

## Model batches and output

Fields are sorted and partitioned within each family into batches of at most four. A family with up to four fields keeps its name; larger families use `Market:part1`, `Market:part2`, and so on. `assessment_batches` maps every planned batch to its family, field names, part number and part count. Successful entries in `groups` include the same mapping; `group_failures` identifies failed batches.

Planned model requests equal the sum of `ceil(supplied_fields_in_family / 4)` across populated families, except deterministic skips. Cache hits avoid repeated inference. This is two requests for the included three-field example and 28 for the union of all 102 definitions. Actual latency depends on the checkpoint, content, device, cache and scheduler. Token budgets still apply to each batch; four long strings are not guaranteed to fit.

The model sees source identity, source name and observation time, plus each batch's values, units, windows and field-clock offsets from the source observation. No verbose catalog descriptions are added to the model state. Cross-field constraints and arithmetic are owned by deterministic code; there is no implied model comparison across separate batches.

| Output member | Meaning |
| --- | --- |
| `assessment_id` | Content-addressed identifier for the persisted final result |
| `observation_id`, `source`, `identity`, `observed_at` | Source and asset context |
| `observation_hash`, `evidence` | Full normalized input fingerprint and archive references |
| `policy` | Policy version, numeric configuration and answer-probability gate |
| `evaluation_started_at`, `evaluated_at`, `clock_mode`, `valid_until` | Evaluation and expiry semantics |
| `catalog_version`, `catalog_sha256`, `task_version` | Interpretation and question provenance |
| `disposition`, `reasons` | Final `candidate`, `review` or `skip` and retained reason codes |
| `assessment_batches`, `groups`, `group_failures` | Complete batch plan, successful answers and failures |
| `deterministic_metrics` | Available descriptive calculations with formulas and provenance |
| `field_notes`, `notes` | Source interpretation and usage limits |
| `execution_authorized` | Always false |

A final result is persisted with `ledger.record_assessment()` even when it is a skip or the backend manifest is unavailable. Retrieve it using `ledger.get_assessment(result['assessment_id'])`. A storage failure is raised; an unrecorded success is not returned.

## Derived metrics

| Metric | Formula | Additional condition |
| --- | --- | --- |
| `buy_share` | buys / (buys + sells) | Same explicit window; positive total |
| `net_buy_volume` | buy_volume − sell_volume | Same explicit window and denomination |
| `liquidity_to_market_cap` | liquidity / market_cap | Positive market cap |
| `circulating_supply_fraction` | circulating_supply / total_supply | Positive total supply; fraction at most one |

Inputs must be semantically valid, share source evidence and observation time, and have compatible units/windows. Ambiguous or inconsistent inputs suppress the affected metric. Each metric records the input keys, formula, unit, window, observation time and evidence. These aggregate calculations do not identify trades, infer guaranteed profit or authorize an order.
