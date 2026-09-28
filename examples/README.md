# Examples

| Example | Contents |
| --- | --- |
| [Market window](market-window-2026-09-28/README.md) | All contracts, quote curves, native assessments and exit-policy timelines |
| [Token index](market-window-2026-09-28/tokens/README.md) | One page per network and contract, including every pool series |
| [Strategy request](strategy.jsonl) | Observation, account, position and policy input |
| [Partial coverage](strategy-partial.jsonl) | Entry request using the parameters actually supplied |
| [Observation input](input.jsonl) | Source data assessment without position decisions |

Market-window curves retain every quote and end at the last observed timestamp. Each contract links to its source parameters and native assessments when present in the captured cohort.

## Inspect and verify

Open a token from the index to inspect its independent pool curves, complete
quote timeline, native assessments and calculated exit-policy events. Price
multiples use the first captured quote. Native model answers belong only to the
assessed observations; neighboring series do not inherit them.

```bash
omnia-trading-casebook verify examples/market-window-2026-09-28
```

Verification uses file hashes, native request/answer bindings and recalculated
quote results. No model download, provider credentials or RPC calls are required.
