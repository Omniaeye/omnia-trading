<p align="center"><img src="assets/eye.png" width="112" alt="OMNIA EYE" /></p>
<h1 align="center">OMNIA TRADING</h1>
<p align="center"><strong>Market intelligence. Position decisions.</strong></p>
<p align="center">Powered by JEV/LAYA &middot; Robinhood Chain &middot; BSC &middot; Solana</p>
<p align="center"><a href="#decisions">Decisions</a> &middot; <a href="#quickstart">Quickstart</a> &middot; <a href="docs/STRATEGY.md">Strategy</a> &middot; <a href="docs/PARAMETERS.md">Parameters</a> &middot; <a href="docs/API.md">API</a></p>
<p align="center"><a href="https://github.com/Omniaeye/omnia-trading/actions/workflows/checks.yml"><img alt="Product checks" src="https://github.com/Omniaeye/omnia-trading/actions/workflows/checks.yml/badge.svg" /></a></p>

---

OMNIA Trading evaluates market observations and turns them into position decisions. JEV/LAYA assesses the evidence. Configurable rules control entry conditions, exposure, profit-taking and downside thresholds.

**SKIP &middot; BUY &middot; HOLD &middot; HOLD BAG &middot; PROFIT &middot; TP &middot; SL**

The Python package combines **102 source parameter definitions**, typed model assessments, position snapshots and a persistent decision ledger. Every result identifies the observation, position, policy and evidence used.

## Decisions

| Decision | Trigger | Result |
| --- | --- | --- |
| **SKIP** | Entry conditions fail, evidence requires attention or a position exceeds exposure limits | No position change proposed; reason codes identify the condition |
| **BUY** | No open position; data, flow, ownership, risk and available budget pass policy | Entry notional in USD |
| **HOLD** | An open position remains within exit limits and risk assessment passes | Keep the current position |
| **HOLD BAG** | Partial profit has been recorded and the remaining quantity is within the configured residual allowance | Keep the residual position; TP and SL remain active |
| **PROFIT** | The partial-profit threshold is reached for the first time | Reduce quantity to the configured residual allocation |
| **TP** | Return from average entry reaches the take-profit threshold | Propose closing the remaining quantity |
| **SL** | Return from average entry reaches the stop-loss threshold | Propose closing the remaining quantity |

The API uses `HOLD_BAG`; interfaces can display **HOLD BAG**. A return is measured from the position's average entry price, before execution costs. `PROFIT` describes a partial-exit decision; it does not assert that a sale has settled.

## From observation to decision

```text
Market observations
        |
        v
Identity, units, windows and freshness
        |
        v
JEV/LAYA data assessment
        |
        v
Strategy checks <----- Account and position
(risk, flow, ownership)
        |
        v
Entry, exposure and exit rules
        |
        v
Decision + sizing + evidence
```

The original data API returns `candidate`, `review` or `skip`. The strategy API adds the seven position decisions. A data candidate is not automatically a BUY.

JEV/LAYA evaluates three specific strategy questions:

- **Risk:** do the supplied reports indicate a transfer restriction, failed sell check, honeypot or wash trading?
- **Flow:** do comparable buy counts exceed sell counts within the same observation window?
- **Ownership:** is the reported top-ten holder share within the configured limit?

Deterministic rules enforce the exact thresholds. A model response cannot override an invalid unit, expired observation, explicit entry rejection or exposure limit. Position exit thresholds take precedence over the additional strategy-model answers after the underlying data assessment passes.

## Parameters

| Family | Definitions | Coverage |
| --- | ---: | --- |
| Market | 28 | Price, capitalization, liquidity, supply, activity, buy/sell volumes, reserves and price impact |
| Holders | 17 | Holder counts, concentration, creator exposure, balances and ownership changes |
| Risk | 19 | Taxes, transfer controls, authority addresses and source-reported security flags |
| Lifecycle | 17 | Launch state, event times, creator, contract, block and slot |
| Social | 21 | Profiles, attention, followers, source links and status |
| **Total** | **102** | **[Types, units, windows and network applicability](docs/PARAMETERS.md)** |

Each observation preserves its value, unit, time window, timestamp and evidence reference. The complete supplied observation goes through data assessment in bounded batches; task-specific strategy checks consume the fields they need. The catalog describes accepted inputs, while an adapter determines which inputs its source provides.

Strategy adds a separate account and position contract: available cash, portfolio exposure, held quantity, initial quantity, average entry price, realized P&L and partial-profit state.

## Configure the strategy

| Parameter | Default | Purpose |
| --- | ---: | --- |
| `entry_budget_usd` | 100 | Proposed entry notional |
| `max_position_usd` | 500 | Maximum position value |
| `max_portfolio_exposure_usd` | 5,000 | Maximum total marked exposure |
| `min_buy_share` | 0.60 | Minimum buys / (buys + sells) for entry |
| `flow_window_seconds` | 300 | Required window for entry counts |
| `max_top_10_holder_ratio` | 0.50 | Top-ten holder concentration limit |
| `max_tax_ratio` | 0.05 | Limit for supplied buy/sell taxes |
| `stop_loss_ratio` | 0.10 | Downside exit threshold |
| `profit_trigger_ratio` | 0.25 | First partial-profit threshold |
| `take_profit_ratio` | 0.50 | Full take-profit threshold |
| `bag_fraction` | 0.20 | Residual fraction of initial quantity |

These are configurable package defaults, not a return forecast. The separate data policy defaults to USD 30,000 minimum market cap, USD 10,000 minimum liquidity and 120-second freshness.

**Position example:** average entry USD 1.00, initial quantity 100. At USD 1.25, PROFIT proposes reducing 80 units and retaining 20. After the application records that fill, the remaining 20 can receive HOLD BAG. At USD 1.50 the policy returns TP; at USD 0.90 it returns SL. Actual proceeds depend on the external execution system.

## Quickstart

Python 3.10 or newer:

```bash
git clone https://github.com/Omniaeye/omnia-trading.git
cd omnia-trading
python -m pip install '.[local]'
```

Select the pinned English checkpoint:

```bash
export OMNIA_LAYA_REVISION=55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851
omnia-trading --catalog
omnia-trading --strategy-policy
omnia-trading --strategy --input strategy-observations.jsonl
```

PowerShell:

```powershell
$env:OMNIA_LAYA_REVISION = '55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851'
omnia-trading --strategy --input strategy-observations.jsonl
```

Each strategy line contains `observation`, `context` and `strategy_policy`. Use the [complete input example](examples/strategy.jsonl) for its shape and supply current source timestamps and position state. Omitted policy members use the defaults above.

For data-quality assessment alone:

```bash
omnia-trading --input observations.jsonl
```

## Python integration

```python
from omnia_trading.strategy import decide
from omnia_trading.strategy_contracts import StrategyPolicy

result = decide(
    observation,
    account_context,
    ledger,
    backend,
    strategy_policy=StrategyPolicy(
        entry_budget_usd=100,
        profit_trigger_ratio=0.25,
        take_profit_ratio=0.50,
        bag_fraction=0.20,
    ),
)

print(result["action"], result["sizing"], result["reasons"])
```

`backend` is the local JEV/LAYA integration; `ledger` is a `DecisionLedger`. [API setup](docs/API.md) and [strategy contract](docs/STRATEGY.md) describe initialization, input types and output fields.

## Decision records

Every strategy result includes a durable assessment ID, input and position fingerprints, policy configuration, model answers, reason codes, sizing and expiry. The decision key binds a proposal to its observation and account snapshot.

The application owns fills and position updates. A repeated decision is not an additional order: consumers deduplicate proposals, verify current account state and recheck expiry before acting. `execution_authorized` remains `false`; wallet signing, order submission and settlement belong to the execution adapter.

## Documentation

| Reference | Contents |
| --- | --- |
| [Strategy](docs/STRATEGY.md) | Decision precedence, position lifecycle, policy and examples |
| [Parameters](docs/PARAMETERS.md) | All 102 source field definitions |
| [API](docs/API.md) | Data and strategy interfaces |
| [Architecture](docs/ARCHITECTURE.md) | Model boundaries, storage and processing |
| [Operations](docs/OPERATIONS.md) | Configuration, replay, recovery and deployment |
| [Research](docs/RESEARCH.md) | Research and runtime foundations |

OMNIA Trading uses the attributed [OMNIA LAYA](https://github.com/Omniaeye/omnia-laya) integration. [OMNIA MCP](https://github.com/Omniaeye/omnia-mcp) and [OMNIA Chronicle](https://github.com/Omniaeye/omnia-chronicle) are separate components in the OMNIA ecosystem.

&copy; 2026 OMNIA EYE Corporation. [Apache-2.0](LICENSE) &middot; [Third-party notices](THIRD_PARTY_NOTICES.md) &middot; [Security](SECURITY.md)
