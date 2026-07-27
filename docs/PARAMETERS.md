# Parameter catalog

102 executable input definitions across Market, Holders, Risk, Lifecycle and Social.

Each supplied field retains its value, unit, window, observation time and evidence reference. The catalog defines accepted adapter inputs. Optional absence is allowed; supplied null values require review. Collection coverage is established separately by the adapter.

Run `omnia-trading --catalog` for the machine-readable schema and fingerprint. This page is generated with `python tools/render_parameters.py` from that same catalog.

## Reading the contract

- Units are case-sensitive accepted spellings; monetary policy uses `USD`.
- Proportion bounds below are expressed as ratios. `50 percent` corresponds to `0.5 ratio`.
- A snapshot requires a null window. An aggregate requires an explicit window.
- Event times use timezone-aware `UTC` text or declared Unix seconds/milliseconds.
- Values outside a domain remain source evidence but prevent automatic promotion.
- Addresses are checked against the declared network family.

See [API](API.md) for envelope shape, review reasons, derived metrics and examples.

## Market — 28 fields

| Parameter | Type | Units | Domain | Window | Networks |
|---|---|---|---|---|---|
| `price` | number | `USD`, `native` | min 0 | snapshot / null | robinhood, bsc, solana |
| `market_cap` | number | `USD`, `native` | min 0 | snapshot / null | robinhood, bsc, solana |
| `liquidity` | number | `USD`, `native` | min 0 | snapshot / null | robinhood, bsc, solana |
| `initial_liquidity` | number | `USD`, `native` | min 0 | snapshot / null | robinhood, bsc, solana |
| `history_highest_market_cap` | number | `USD`, `native` | min 0 | snapshot / null | robinhood, bsc, solana |
| `total_supply` | number | `tokens`, `Tokens` | min 0 | snapshot / null | robinhood, bsc, solana |
| `volume` | number | `USD`, `native` | min 0 | explicit aggregate window | robinhood, bsc, solana |
| `volume_24h` | number | `USD`, `native` | min 0 | 86400 s | robinhood, bsc, solana |
| `buys` | integer | `count`, `Count` | min 0 | explicit aggregate window | robinhood, bsc, solana |
| `sells` | integer | `count`, `Count` | min 0 | explicit aggregate window | robinhood, bsc, solana |
| `swaps` | integer | `count`, `Count` | min 0 | explicit aggregate window | robinhood, bsc, solana |
| `buys_24h` | integer | `count`, `Count` | min 0 | 86400 s | robinhood, bsc, solana |
| `sells_24h` | integer | `count`, `Count` | min 0 | 86400 s | robinhood, bsc, solana |
| `price_change_percent` | number | `ratio`, `percent`, `%` | min -1 | explicit aggregate window | robinhood, bsc, solana |
| `price_change_percent1m` | number | `ratio`, `percent`, `%` | min -1 | 60 s | robinhood, bsc, solana |
| `price_change_percent5m` | number | `ratio`, `percent`, `%` | min -1 | 300 s | robinhood, bsc, solana |
| `price_change_percent1h` | number | `ratio`, `percent`, `%` | min -1 | 3600 s | robinhood, bsc, solana |
| `gas_fee` | number | `USD`, `native` | min 0 | snapshot / null | robinhood, bsc, solana |
| `rank` | integer | `count`, `Count` | min 1 | snapshot / null | robinhood, bsc, solana |
| `circulating_supply` | number | `tokens`, `Tokens` | min 0 | snapshot / null | robinhood, bsc, solana |
| `fdv` | number | `USD`, `native` | min 0 | snapshot / null | robinhood, bsc, solana |
| `buy_volume` | number | `USD`, `native` | min 0 | explicit aggregate window | robinhood, bsc, solana |
| `sell_volume` | number | `USD`, `native` | min 0 | explicit aggregate window | robinhood, bsc, solana |
| `unique_buyers` | integer | `count`, `Count` | min 0 | explicit aggregate window | robinhood, bsc, solana |
| `unique_sellers` | integer | `count`, `Count` | min 0 | explicit aggregate window | robinhood, bsc, solana |
| `quote_reserve` | number | `tokens`, `Tokens` | min 0 | snapshot / null | robinhood, bsc, solana |
| `base_reserve` | number | `tokens`, `Tokens` | min 0 | snapshot / null | robinhood, bsc, solana |
| `price_impact_bps` | number | `bps` | min 0, max 10000 | snapshot / null | robinhood, bsc, solana |

### Meaning and evidence

**`price` — Price**

Price reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`market_cap` — Market cap**

Market cap reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`liquidity` — Liquidity**

Liquidity reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`initial_liquidity` — Initial liquidity**

Initial liquidity reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`history_highest_market_cap` — History highest market cap**

History highest market cap reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`total_supply` — Total supply**

Total supply reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`volume` — Volume · ranking window**

Volume in the ranking window reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`volume_24h` — Volume 24 hours**

Volume 24 hours reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`buys` — Buys · ranking window**

Buys in the ranking window reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`sells` — Sells · ranking window**

Sells in the ranking window reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`swaps` — Swaps · ranking window**

Swaps in the ranking window reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`buys_24h` — Buys 24 hours**

Buys 24 hours reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`sells_24h` — Sells 24 hours**

Sells 24 hours reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`price_change_percent` — Price change · ranking window**

Price change in the ranking window reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`price_change_percent1m` — Price change · 1 minute**

Price change in the 1 minute reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`price_change_percent5m` — Price change · 5 minutes**

Price change in the 5 minutes reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`price_change_percent1h` — Price change · 1 hour**

Price change in the 1 hour reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`gas_fee` — Gas fee**

Gas fee reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`rank` — Rank**

Rank reported by the source adapter.

Positive source rank; no cross-source ranking equivalence is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`circulating_supply` — Circulating supply**

Source-reported circulating supply, separate from total supply and FDV.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`fdv` — Fully diluted valuation**

Source-reported fully diluted valuation. It is not substituted for circulating market capitalization.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`buy_volume` — Buy volume**

Aggregate buy-side volume over the explicitly declared window.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`sell_volume` — Sell volume**

Aggregate sell-side volume over the explicitly declared window.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`unique_buyers` — Unique buyers**

Distinct buying addresses within the declared source window; not an independently identified person count.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`unique_sellers` — Unique sellers**

Distinct selling addresses within the declared source window; not an independently identified person count.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`quote_reserve` — Quote reserve**

Pool quote-asset reserve. The adapter must bind the quote asset; this value is not automatically USD.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`base_reserve` — Base reserve**

Pool base-token reserve from the source capture; no executable depth guarantee is implied.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`price_impact_bps` — Quoted price impact**

Source-reported nonnegative price-impact magnitude in basis points for a separately archived quote, size and route.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.


## Holders — 17 fields

| Parameter | Type | Units | Domain | Window | Networks |
|---|---|---|---|---|---|
| `holder_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `top_10_holder_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `creator_balance_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `dev_team_hold_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `rat_trader_amount_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `bluechip_owner_percentage` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `sniper_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `smart_degen_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `renowned_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `bundler_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `top70_sniper_hold_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `bot_degen_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `bot_degen_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `top_1_holder_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `insider_hold_rate` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `holder_count_change` | integer | `count`, `Count` | type constrained | explicit aggregate window | robinhood, bsc, solana |
| `creator_token_balance` | number | `tokens`, `Tokens` | min 0 | snapshot / null | robinhood, bsc, solana |

### Meaning and evidence

**`holder_count` — Holder count**

Holder count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`top_10_holder_rate` — Top 10 holder rate**

Top 10 holder rate reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`creator_balance_rate` — Creator balance rate**

Creator balance rate reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`dev_team_hold_rate` — Dev team hold rate**

Dev team hold rate reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`rat_trader_amount_rate` — Flagged trader amount ratio**

Flagged trader amount ratio reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`bluechip_owner_percentage` — Blue-chip ownership**

Blue-chip ownership reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`sniper_count` — Sniper count**

Sniper count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`smart_degen_count` — Smart trader count**

Smart trader count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`renowned_count` — Recognized trader count**

Recognized trader count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`bundler_rate` — Bundler rate**

Bundler rate reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`top70_sniper_hold_rate` — Top70 sniper hold rate**

Top70 sniper hold rate reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`bot_degen_count` — Bot trader count**

Bot trader count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`bot_degen_rate` — Bot trader ratio**

Bot trader ratio reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`top_1_holder_rate` — Largest holder share**

Share attributed to the largest holder under the source denominator and exclusion rules.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`insider_hold_rate` — Source-tagged insider share**

Holder share tagged as insider-related by the source; the label is not independent attribution.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`holder_count_change` — Holder count change**

Signed change in an aggregate holder count across the declared window, not identified joins or exits.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`creator_token_balance` — Creator token balance**

Token balance attributed to the creator address by the source.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.


## Risk — 19 fields

| Parameter | Type | Units | Domain | Window | Networks |
|---|---|---|---|---|---|
| `buy_tax` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `sell_tax` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `is_honeypot` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `is_wash_trading` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `renounced_mint` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `renounced_freeze_account` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `burn_ratio` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `burn_status` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `dev_token_burn_amount` | number | `tokens`, `Tokens` | min 0 | snapshot / null | robinhood, bsc, solana |
| `dev_token_burn_ratio` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `rug_ratio` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `entrapment_ratio` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `is_renounced` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `is_open_source` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `lock_percent` | number | `ratio`, `percent`, `%` | min 0, max 1 | snapshot / null | robinhood, bsc, solana |
| `mint_authority` | address | `address`, `Address` | type constrained | snapshot / null | solana |
| `freeze_authority` | address | `address`, `Address` | type constrained | snapshot / null | solana |
| `transfer_paused` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `sell_simulation_success` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |

### Meaning and evidence

**`buy_tax` — Buy tax**

Buy tax reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`sell_tax` — Sell tax**

Sell tax reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`is_honeypot` — Is honeypot**

Is honeypot reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`is_wash_trading` — Is wash trading**

Is wash trading reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`renounced_mint` — Renounced mint**

Renounced mint reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`renounced_freeze_account` — Renounced freeze account**

Renounced freeze account reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`burn_ratio` — Burn ratio**

Burn ratio reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`burn_status` — Burn status**

Burn status reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`dev_token_burn_amount` — Dev token burn amount**

Dev token burn amount reported by the source adapter.

Source-reported value. Only an explicit allowed unit is interpretable; raw or unknown denomination remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`dev_token_burn_ratio` — Dev token burn ratio**

Dev token burn ratio reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`rug_ratio` — Source rug ratio**

Source rug ratio reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`entrapment_ratio` — Source entrapment ratio**

Source entrapment ratio reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`is_renounced` — Is renounced**

Is renounced reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`is_open_source` — Is open source**

Is open source reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`lock_percent` — Lock percent**

Lock percent reported by the source adapter.

Explicit ratio and percent units are distinguished. Domain bounds are expressed as ratios; raw source scale remains review.
Missingness: `optional_absent; supplied_null_requires_review`.

**`mint_authority` — Mint authority**

Source-reported Solana mint authority address. An absent authority must be expressed through an explicit source flag, not an invented address.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`freeze_authority` — Freeze authority**

Source-reported Solana freeze authority address. Syntactic validity does not establish current authority.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`transfer_paused` — Transfers paused**

Source-reported transfer-pause state; false is not a general transferability guarantee.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`sell_simulation_success` — Sell simulation succeeded**

Result reported for a separately archived sell simulation. It does not prove a real fill or future sellability.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.


## Lifecycle — 17 fields

| Parameter | Type | Units | Domain | Window | Networks |
|---|---|---|---|---|---|
| `launchpad` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `launchpad_platform` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `launchpad_status` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `created_timestamp` | timestamp | `UTC`, `unix_seconds`, `unix_milliseconds` | type constrained | snapshot / null | robinhood, bsc, solana |
| `creation_timestamp` | timestamp | `UTC`, `unix_seconds`, `unix_milliseconds` | type constrained | snapshot / null | robinhood, bsc, solana |
| `open_timestamp` | timestamp | `UTC`, `unix_seconds`, `unix_milliseconds` | type constrained | snapshot / null | robinhood, bsc, solana |
| `complete_timestamp` | timestamp | `UTC`, `unix_seconds`, `unix_milliseconds` | type constrained | snapshot / null | robinhood, bsc, solana |
| `pool_type` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `pool_type_str` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `exchange` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `creator` | address | `address`, `Address` | type constrained | snapshot / null | robinhood, bsc, solana |
| `creator_token_status` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `creator_close` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `launch_quote_address` | address | `address`, `Address` | type constrained | snapshot / null | robinhood, bsc, solana |
| `migrated_pool_exchange` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `block_number` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc |
| `slot` | integer | `count`, `Count` | min 0 | snapshot / null | solana |

### Meaning and evidence

**`launchpad` — Launchpad**

Launchpad reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`launchpad_platform` — Launchpad platform**

Launchpad platform reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`launchpad_status` — Launchpad status**

Launchpad status reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`created_timestamp` — Created timestamp**

Created timestamp reported by the source adapter.

Source event time. Zero is unknown. UTC requires timezone-aware text; numeric epochs require an explicit seconds or milliseconds unit.
Missingness: `optional_absent; supplied_null_requires_review`.

**`creation_timestamp` — Creation timestamp**

Creation timestamp reported by the source adapter.

Source event time. Zero is unknown. UTC requires timezone-aware text; numeric epochs require an explicit seconds or milliseconds unit.
Missingness: `optional_absent; supplied_null_requires_review`.

**`open_timestamp` — Open timestamp**

Open timestamp reported by the source adapter.

Source event time. Zero is unknown. UTC requires timezone-aware text; numeric epochs require an explicit seconds or milliseconds unit.
Missingness: `optional_absent; supplied_null_requires_review`.

**`complete_timestamp` — Complete timestamp**

Complete timestamp reported by the source adapter.

Source event time. Zero is unknown. UTC requires timezone-aware text; numeric epochs require an explicit seconds or milliseconds unit.
Missingness: `optional_absent; supplied_null_requires_review`.

**`pool_type` — Pool type code**

Pool type code reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`pool_type_str` — Pool type str**

Pool type str reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`exchange` — Exchange**

Exchange reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`creator` — Creator**

Creator reported by the source adapter.

Address syntax must match the observation chain. No ownership, affiliation, contract-code or on-chain lookup is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`creator_token_status` — Creator token status**

Creator token status reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`creator_close` — Creator close**

Creator close reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`launch_quote_address` — Launch quote address**

Launch quote address reported by the source adapter.

Address syntax must match the observation chain. No ownership, affiliation, contract-code or on-chain lookup is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`migrated_pool_exchange` — Migrated pool exchange**

Migrated pool exchange reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`block_number` — EVM block number**

Source observation block number, without an implied finality or canonical-chain guarantee.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.

**`slot` — Solana slot**

Source observation slot, without an implied finality guarantee.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.


## Social — 21 fields

| Parameter | Type | Units | Domain | Window | Networks |
|---|---|---|---|---|---|
| `twitter_username` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `twitter` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `twitter_handle` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `website` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `telegram` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `twitter_change_flag` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `twitter_rename_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `twitter_del_post_token_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `twitter_create_token_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `twitter_dup` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `telegram_dup` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `website_dup` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `square_mentions` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `visiting_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |
| `hot_level` | text | `text`, `source_value`, `Source value` | type constrained | snapshot / null | robinhood, bsc, solana |
| `is_show_alert` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `is_og` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `is_token_live` | boolean | `boolean`, `Source flag` | type constrained | snapshot / null | robinhood, bsc, solana |
| `start_live_timestamp` | timestamp | `UTC`, `unix_seconds`, `unix_milliseconds` | type constrained | snapshot / null | robinhood, bsc, solana |
| `end_live_timestamp` | timestamp | `UTC`, `unix_seconds`, `unix_milliseconds` | type constrained | snapshot / null | robinhood, bsc, solana |
| `twitter_follower_count` | integer | `count`, `Count` | min 0 | snapshot / null | robinhood, bsc, solana |

### Meaning and evidence

**`twitter_username` — Twitter username**

Twitter username reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`twitter` — X reference**

X reference reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`twitter_handle` — X handle**

X handle reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`website` — Website**

Website reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`telegram` — Telegram**

Telegram reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`twitter_change_flag` — Twitter change flag**

Twitter change flag reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`twitter_rename_count` — Twitter rename count**

Twitter rename count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`twitter_del_post_token_count` — Twitter del post token count**

Twitter del post token count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`twitter_create_token_count` — Twitter create token count**

Twitter create token count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`twitter_dup` — Twitter dup**

Twitter dup reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`telegram_dup` — Telegram dup**

Telegram dup reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`website_dup` — Website dup**

Website dup reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`square_mentions` — Square mentions**

Square mentions reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`visiting_count` — Visiting count**

Visiting count reported by the source adapter.

A nonnegative whole-number source count; it does not identify individual participants or transactions.
Missingness: `optional_absent; supplied_null_requires_review`.

**`hot_level` — Source hot level**

Source hot level reported by the source adapter.

Source-supplied text. No independent truth, affiliation or availability verification is implied.
Missingness: `optional_absent; supplied_null_requires_review`.

**`is_show_alert` — Is show alert**

Is show alert reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`is_og` — Is og**

Is og reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`is_token_live` — Is token live**

Is token live reported by the source adapter.

Explicit source-reported boolean. A false flag alone is not a security guarantee.
Missingness: `optional_absent; supplied_null_requires_review`.

**`start_live_timestamp` — Start live timestamp**

Start live timestamp reported by the source adapter.

Source event time. Zero is unknown. UTC requires timezone-aware text; numeric epochs require an explicit seconds or milliseconds unit.
Missingness: `optional_absent; supplied_null_requires_review`.

**`end_live_timestamp` — End live timestamp**

End live timestamp reported by the source adapter.

Source event time. Zero is unknown. UTC requires timezone-aware text; numeric epochs require an explicit seconds or milliseconds unit.
Missingness: `optional_absent; supplied_null_requires_review`.

**`twitter_follower_count` — X follower count**

Source-reported follower count for the associated profile; association is not verified affiliation.

Optional adapter input. Catalog support does not mean this field is collected or independently verified.
Missingness: `optional_absent; supplied_null_requires_review`.
