# Quote performance and conditional exits

`performance.summarize_quotes(points)` computes observed price changes and an
independent entry scenario. It does not call LAYA or the position strategy.

Each point contains `at`, `price` and `evidence`. The caller must partition
chain, network, token, pool and source and establish a common price unit first.
The function sorts timestamps, rejects duplicate clocks and invalid prices,
and requires at least two quotes. Missing coverage is not a zero return.

## Observed market results

- Final return: last quote / first quote âˆ’ 1.
- Peak multiple: highest observed quote / first quote.
- Maximum drawdown: largest decline from a previous observed peak.
- 2x, 3x, 5x and 10x milestones: first observed quote meeting each multiple.
- Gaps: maximum interval between recorded quotes.

Milestones describe quotes, not fills. An asset that reaches 2x can close below
2x. Tokens that disappear from the ranking retain their last available quote;
the report must expose their first/last timestamps rather than assume coverage
through the entire capture window. Comparisons are descriptive, not a cohort
backtest with identical observation horizons.

## Conditional position scenario

The reference scenario buys $100 at the first quote. The next observed quote
selects SL at âˆ’10%, TP at +50%, or a one-time PROFIT reduction of 80% at +25%.
The residual position is HOLD_BAG; other open positions are HOLD. Full exits
prevent re-entry. Price thresholds and bag size come from `StrategyPolicy`.

Exit accounting uses the observed price, not an unobserved target price. Cash
flows and remaining cost basis separate realized scenario P&L from unrealized
scenario P&L. Both sum to final gross scenario P&L. Fees, price impact, slippage
and liquidity availability are excluded. Each token has independent capital;
these results do not represent a shared portfolio or executable returns.

These BUY/PROFIT/TP/SL events must not be attributed to the model. Actual entry
prechecks and recorded native answers appear separately in the report. No
account snapshot or execution receipt is fabricated to produce an action.

## Private report

```bash
omnia-trading-report \
  --capture-dir /private/five-minute-capture \
  --output-dir /private/performance-review
```

The capture directory supplies `manifest.json`, `sample.json`,
`task-results.jsonl` and `raw/<capture_id>.json`. Ranking bytes must match the
manifest hashes. Only the documented ranking price path enters the series;
unverified launch prices and unrelated candle history are not mixed in.

The output contains `report.json`. The casebook exporter produces Markdown indexes,
per-contract quote curves and complete JSON/CSV records. The output directory must be new.

## Published window

[28 September 2026](../examples/market-window-2026-09-28/README.md) includes all contracts, native inputs/answers and per-series records. Verify it with `omnia-trading-casebook verify examples/market-window-2026-09-28`.
