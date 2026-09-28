# Examples

Start with the recorded market window to inspect data and results. Use the input
contracts when connecting your own source and account state.

| Example | Contents | Run |
| --- | --- | --- |
| [Market window: 28 September](market-window-2026-09-28/README.md) | Three networks, 60 assessed observations, 180 native responses and all 621 report series | `omnia-trading-casebook verify examples/market-window-2026-09-28` |
| [Complete strategy input](strategy.jsonl) | Observation, account, position and policy envelope | Supply current source and account timestamps, then use `omnia-trading --strategy --input your-input.jsonl` |
| [Minimal entry input](strategy-partial.jsonl) | Price and aligned buy/sell activity; optional reports omitted | Same strategy command with your source data |
| [Observation input](input.jsonl) | Data assessment without position decisions | `omnia-trading --input your-observations.jsonl` |

## Read a contract record

1. Open a network index: [Robinhood](market-window-2026-09-28/series/robinhood/README.md), [BSC](market-window-2026-09-28/series/bsc/README.md), or [Solana](market-window-2026-09-28/series/solana/README.md).
2. Select a token's **Inspect** link. Identity includes network, contract and pool.
3. `points` contains each captured price and source reference.
4. `performance.market` contains peak, last price, milestones and observed drawdown.
5. `performance.scenario.events` contains the calculated exit-policy timeline.
6. `evaluations` contains any entry precheck captured for that series. The model
   cohort has 60 observations; other series do not acquire model answers by association.

The [contract records](market-window-2026-09-28/README.md#contract-records) include
all supplied parameters and the original native model inputs and outputs.

## Files and provenance

`manifest.json` records hashes of every published file. Verification also binds
model requests to observation fields and recalculates the price results. It uses
no provider credentials, RPC, database service or model download.

Provider payloads and local databases remain in the capture archive. The public
package contains normalized market observations, native inference records, quote
trajectories and source hashes. A checksum demonstrates consistency with a
recorded file, not an independent attestation of a provider's market data.
