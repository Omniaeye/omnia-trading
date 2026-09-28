# Position strategy

OMNIA Trading separates source-data acceptance from position decisions. The strategy API returns `omnia.trading.strategy.v2` and records source coverage alongside each assessment.

## Interfaces

```python
from omnia_trading._engine.ledger import DecisionLedger
from omnia_trading._engine.runtime import LocalLaya
from omnia_trading.config import Config
from omnia_trading.strategy import decide, process_strategy
from omnia_trading.strategy_contracts import StrategyPolicy

config = Config.from_env()
ledger = DecisionLedger(config.runtime.database)
backend = LocalLaya(config.runtime)
try:
    result = decide(
        observation, context, ledger, backend,
        strategy_policy=StrategyPolicy(),
        data_policy=config.policy(),
        min_probability=config.runtime.min_probability,
        max_bytes=config.runtime.max_bytes,
    )
finally:
    ledger.close()
```

`decide` accepts an observation, context, ledger and backend. Keyword options are `strategy_policy`, `data_policy`, `min_probability`, `max_bytes` and `now`. An explicit timezone-aware `now` selects historical replay.

`process_strategy` accepts an envelope containing exactly `observation`, `context` and `strategy_policy`. The policy is a dictionary of zero or more named overrides. Unknown options are rejected.

## Account context

| Member | Meaning |
| --- | --- |
| `identity` | Exact normalized chain, network, contract and pool of the observation |
| `observed_at` | Time of the account/position snapshot, with timezone |
| `evidence` | Reference to the account snapshot |
| `cash_available_usd` | Unreserved capital available for this account |
| `portfolio_exposure_usd` | Total marked exposure, including the current position |
| `position` | Null for entry evaluation, otherwise the open-position object |

An open position has exactly:

| Member | Constraint |
| --- | --- |
| `id` | Nonempty position identifier |
| `quantity` | Positive held quantity |
| `initial_quantity` | Positive initial quantity, at least the held quantity |
| `average_entry_price_usd` | Positive average entry price |
| `profit_taken` | Boolean indicating a recorded partial-profit fill |
| `realized_pnl_usd` | Finite realized P&L; negative values are allowed |

Use one position lot with a fixed initial quantity. Pyramiding and multiple lots require aggregation in the account adapter. The strategy does not mutate positions or infer fills from its previous decisions. Update the position from reconciled execution records. Reset to null only after the position is closed.

## Policy

All ratios use fractions: 0.10 means 10%. Source fields may use explicit percentage units; the field normalizer converts only known scales.

| Option | Default | Constraint / interpretation |
| --- | ---: | --- |
| `entry_budget_usd` | 100 | Positive, no larger than the position limit |
| `max_position_usd` | 500 | Positive, no larger than the portfolio limit |
| `max_portfolio_exposure_usd` | 5000 | Positive total exposure limit |
| `min_buy_share` | 0.60 | Greater than 0 and at most 1 |
| `flow_window_seconds` | 300 | Integer 1-2,592,000 |
| `max_top_10_holder_ratio` | 0.50 | Greater than 0 and at most 1 |
| `max_tax_ratio` | 0.05 | 0-1; applied to supplied taxes |
| `stop_loss_ratio` | 0.10 | Greater than 0 and less than 1 |
| `profit_trigger_ratio` | 0.25 | Positive partial-exit return |
| `take_profit_ratio` | 0.50 | Greater than the partial-profit trigger |
| `bag_fraction` | 0.20 | Greater than 0 and less than 1 |
| `require_risk_reports` | false | Require all four security reports before entry and holding decisions |
| `require_ownership` | false | Require top-ten holder share for entry |

Print executable defaults with `omnia-trading --strategy-policy`. Strategy options are supplied per envelope or through `StrategyPolicy`; they are not implicitly read from environment variables. Runtime and data-policy environment variables continue to use [.env.example](../.env.example).

## Entry prerequisites

Entry requires a candidate data assessment and positive USD price. Market cap, liquidity, source semantics and freshness use the existing data policy.

The minimum entry inputs are a valid asset identity, current positive USD price, comparable buy/sell counts, a current account snapshot and enough budget. The accepted data assessment and the flow model answer remain required.

- Known honeypot, paused transfer, failed sell-check or wash-trading reports reject entry.
- Missing security reports are recorded as partial or not reported. They are not called clear. Risk inference runs only with all four reports; `require_risk_reports=true` makes their presence mandatory.
- Reported top-ten holder share must respect the concentration limit. Absence is allowed unless `require_ownership=true`; ownership inference is skipped when absent.
- Reported market cap and liquidity must use USD and respect their limits. Data-policy requirements can make presence mandatory.
- Supplied buy/sell taxes must respect the tax limit.
- Invalid reported measurements and expired inputs still block promotion.

Existing positions do not require entry-flow or ownership tasks. Risk reports remain evaluated when complete; known rejecting reports still block HOLD and PROFIT. SL and TP retain their documented precedence.

`strategy_coverage` lists each task's reported and missing fields. `strategy_checks` contains only actual model answers. Partial coverage does not establish token safety, and a BUY remains an execution proposal.

## Decision precedence

1. Invalid, mismatched or expired observations/account snapshots produce SKIP.
2. A data result other than candidate produces SKIP.
3. For an open position: SL first, then TP, based on the positive USD price.
4. A position/portfolio exposure breach produces SKIP and a rebalance reason.
5. Risk rejections, incomplete strategy answers or probability-gate failures produce SKIP.
6. The first partial-profit trigger produces PROFIT and an exact reduction proposal.
7. A recorded residual position at or below its bag allowance produces HOLD_BAG.
8. Other eligible open positions produce HOLD.
9. With no open position, all entry checks must pass to produce BUY.

SL and TP do not depend on the additional strategy-model answers. They still require an accepted data assessment and fresh, matching account/price inputs. SKIP with an existing position is an abstention, not a liquidation instruction or protection order. An execution service must maintain its own independent position protection.

Flow and ownership are entry filters. Existing positions use risk inference when its reports are complete; flow and ownership are not additional holding gates. Explicit transfer/manipulation risk blocks HOLD and PROFIT proposals.

## Position lifecycle

For initial quantity 100, average entry USD 1.00 and the default policy:

| Account state | Price | Decision | Sizing |
| --- | ---: | --- | --- |
| Open, no partial profit | 1.10 | HOLD | No reduction |
| Open, no partial profit | 1.25 | PROFIT | Reduce 80; retain 20 |
| Partial fill recorded; quantity 20 | 1.30 | HOLD_BAG | Retain 20 |
| Open at either quantity | 1.50 | TP | Reduce the remaining quantity |
| Open at either quantity | 0.90 | SL | Reduce the remaining quantity |

The examples assume accepted current evidence and all relevant policy checks. The return calculation excludes fees, tax, slippage and realized P&L: `price / average_entry_price_usd - 1`. Realized P&L is retained separately. PROFIT retains `initial_quantity * bag_fraction`; this is not a percentage of the shrinking current balance.

## Results and persistence

| Member | Meaning |
| --- | --- |
| `action` | SKIP, BUY, HOLD, HOLD_BAG, PROFIT, TP or SL |
| `reasons` | Machine-readable rule outcomes |
| `sizing` | Entry notional, reduction/retained quantities and applicable position metrics |
| `data_assessment_id` | Persisted parent data-quality assessment |
| `data_disposition` | Parent candidate/review/skip |
| `strategy_checks` | Risk, flow and ownership decision records |
| `strategy_failures` | Processing error types without raw provider messages |
| `context_hash` | Complete normalized account snapshot fingerprint |
| `position_id` | Position identifier, or null for entry |
| `decision_key` | Proposal fingerprint covering observation, context, policy, action and sizing |
| `assessment_id` | Durable record identifier |
| `valid_until` | Earliest expiry of source data and account context |
| `execution_authorized` | False |

The ledger stores data assessments and strategy assessments separately in the same assessments table. Cached model answers retain their original processing time; freshness and position policy are checked again for the final result.

The decision key supports caller deduplication; it is not a wallet nonce or an execution lock. Different observations of an unchanged position may produce another proposal. The executor must serialize account changes, reserve capital, check position version, apply its own idempotency and reconcile the receipt before updating the context.

## Model context

The quality stage covers every supplied field in bounded batches. Strategy adds up to three closed-choice requests using task-specific subsets:

| Task | Source inputs | Accepted entry answer |
| --- | --- | --- |
| Risk | Honeypot, paused transfer, sell check, wash trading | clear |
| Flow | Buys and sells | supportive |
| Ownership | Top-ten holder share and policy limit | within_limit |

Each record retains its model manifest, evidence references, question fingerprint and probability gate. The probability is model output, not a calibrated financial success probability. No free-text source can change the policy. Requests exceeding the model context budget yield explicit failures.
