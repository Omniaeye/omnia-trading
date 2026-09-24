# Parameter catalog

82 explicit definitions across five families. These are source fields; all
values preserve their supplied units, timestamps, windows and evidence.

## Market

| Key | Label | Source meaning |
| --- | --- | --- |
| `price` | Price | Source denomination — Currency denomination has not been normalized. Ranking-window fields have no confirmed duration in this capture. |
| `market_cap` | Market cap | Source denomination — Currency denomination has not been normalized. Ranking-window fields have no confirmed duration in this capture. |
| `liquidity` | Liquidity | Source denomination — Currency denomination has not been normalized. Ranking-window fields have no confirmed duration in this capture. |
| `initial_liquidity` | Initial liquidity | Source denomination — Currency denomination has not been normalized. Ranking-window fields have no confirmed duration in this capture. |
| `history_highest_market_cap` | History highest market cap | Source denomination — Currency denomination has not been normalized. Ranking-window fields have no confirmed duration in this capture. |
| `total_supply` | Total supply | Tokens — Reported by the source. No independent validation or JEV assessment. |
| `volume` | Volume Â· ranking window | Source denomination — Currency denomination has not been normalized. Ranking-window fields have no confirmed duration in this capture. |
| `volume_24h` | Volume 24 hours | Source denomination — Currency denomination has not been normalized. Ranking-window fields have no confirmed duration in this capture. |
| `buys` | Buys Â· ranking window | Count — Reported by the source. No independent validation or JEV assessment. |
| `sells` | Sells Â· ranking window | Count — Reported by the source. No independent validation or JEV assessment. |
| `swaps` | Swaps Â· ranking window | Count — Reported by the source. No independent validation or JEV assessment. |
| `buys_24h` | Buys 24 hours | Count — Reported by the source. No independent validation or JEV assessment. |
| `sells_24h` | Sells 24 hours | Count — Reported by the source. No independent validation or JEV assessment. |
| `price_change_percent` | Price change Â· ranking window | Raw scale — Source documentation conflicts between percentage and ratio. Value retained without conversion or percent suffix. |
| `price_change_percent1m` | Price change Â· 1 minute | Raw scale — Source documentation conflicts between percentage and ratio. Value retained without conversion or percent suffix. |
| `price_change_percent5m` | Price change Â· 5 minutes | Raw scale — Source documentation conflicts between percentage and ratio. Value retained without conversion or percent suffix. |
| `price_change_percent1h` | Price change Â· 1 hour | Raw scale — Source documentation conflicts between percentage and ratio. Value retained without conversion or percent suffix. |
| `gas_fee` | Gas fee | Source denomination — Currency denomination has not been normalized. Ranking-window fields have no confirmed duration in this capture. |
| `rank` | Rank | Source value — Reported by the source. No independent validation or JEV assessment. |

## Holders

| Key | Label | Source meaning |
| --- | --- | --- |
| `holder_count` | Holder count | Count — Reported by the source. No independent validation or JEV assessment. |
| `top_10_holder_rate` | Top 10 holder rate | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `creator_balance_rate` | Creator balance rate | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `dev_team_hold_rate` | Dev team hold rate | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `rat_trader_amount_rate` | Flagged trader amount ratio | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `bluechip_owner_percentage` | Blue-chip ownership | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `sniper_count` | Sniper count | Count — Reported by the source. No independent validation or JEV assessment. |
| `smart_degen_count` | Smart trader count | Count — Reported by the source. No independent validation or JEV assessment. |
| `renowned_count` | Recognized trader count | Count — Reported by the source. No independent validation or JEV assessment. |
| `bundler_rate` | Bundler rate | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `top70_sniper_hold_rate` | Top70 sniper hold rate | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `bot_degen_count` | Bot trader count | Count — Reported by the source. No independent validation or JEV assessment. |
| `bot_degen_rate` | Bot trader ratio | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |

## Risk

| Key | Label | Source meaning |
| --- | --- | --- |
| `buy_tax` | Buy tax | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `sell_tax` | Sell tax | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `is_honeypot` | Is honeypot | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `is_wash_trading` | Is wash trading | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `renounced_mint` | Renounced mint | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `renounced_freeze_account` | Renounced freeze account | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `burn_ratio` | Burn ratio | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `burn_status` | Burn status | Source value — Reported by the source. No independent validation or JEV assessment. |
| `dev_token_burn_amount` | Dev token burn amount | Tokens — Reported by the source. No independent validation or JEV assessment. |
| `dev_token_burn_ratio` | Dev token burn ratio | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `rug_ratio` | Source rug ratio | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `entrapment_ratio` | Source entrapment ratio | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |
| `is_renounced` | Is renounced | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `is_open_source` | Is open source | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `lock_percent` | Lock percent | Raw scale — Source scale retained. Not converted to a percentage or interpreted as a probability. |

## Lifecycle

| Key | Label | Source meaning |
| --- | --- | --- |
| `launchpad` | Launchpad | Source value — Reported by the source. No independent validation or JEV assessment. |
| `launchpad_platform` | Launchpad platform | Source value — Reported by the source. No independent validation or JEV assessment. |
| `launchpad_status` | Launchpad status | Source value — Reported by the source. No independent validation or JEV assessment. |
| `created_timestamp` | Created timestamp | UTC — Source event time. Zero means no usable event time, not January 1970. |
| `creation_timestamp` | Creation timestamp | UTC — Source event time. Zero means no usable event time, not January 1970. |
| `open_timestamp` | Open timestamp | UTC — Source event time. Zero means no usable event time, not January 1970. |
| `complete_timestamp` | Complete timestamp | UTC — Source event time. Zero means no usable event time, not January 1970. |
| `pool_type` | Pool type code | Source value — Reported by the source. No independent validation or JEV assessment. |
| `pool_type_str` | Pool type str | Source value — Reported by the source. No independent validation or JEV assessment. |
| `exchange` | Exchange | Source value — Reported by the source. No independent validation or JEV assessment. |
| `creator` | Creator | Address — Reported by the source. No independent validation or JEV assessment. |
| `creator_token_status` | Creator token status | Source value — Reported by the source. No independent validation or JEV assessment. |
| `creator_close` | Creator close | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `launch_quote_address` | Launch quote address | Address — Reported by the source. No independent validation or JEV assessment. |
| `migrated_pool_exchange` | Migrated pool exchange | Source value — Reported by the source. No independent validation or JEV assessment. |

## Social

| Key | Label | Source meaning |
| --- | --- | --- |
| `twitter_username` | Twitter username | Source value — Reported by the source. No independent validation or JEV assessment. |
| `twitter` | X reference | Source value — Reported by the launch source. No independent affiliation validation. |
| `twitter_handle` | X handle | Source value — Reported by the launch source. No independent affiliation validation. |
| `website` | Website | Source value — Reported by the source. No independent validation or JEV assessment. |
| `telegram` | Telegram | Source value — Reported by the source. No independent validation or JEV assessment. |
| `twitter_change_flag` | Twitter change flag | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `twitter_rename_count` | Twitter rename count | Count — Reported by the source. No independent validation or JEV assessment. |
| `twitter_del_post_token_count` | Twitter del post token count | Count — Reported by the source. No independent validation or JEV assessment. |
| `twitter_create_token_count` | Twitter create token count | Count — Reported by the source. No independent validation or JEV assessment. |
| `twitter_dup` | Twitter dup | Count — Reported by the source. No independent validation or JEV assessment. |
| `telegram_dup` | Telegram dup | Count — Reported by the source. No independent validation or JEV assessment. |
| `website_dup` | Website dup | Count — Reported by the source. No independent validation or JEV assessment. |
| `square_mentions` | Square mentions | Source value — Reported by the source. No independent validation or JEV assessment. |
| `visiting_count` | Visiting count | Count — Reported by the source. No independent validation or JEV assessment. |
| `hot_level` | Source hot level | Source value — Reported by the source. No independent validation or JEV assessment. |
| `is_show_alert` | Is show alert | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `is_og` | Is og | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `is_token_live` | Is token live | Source flag — Raw source flag; zero or false does not establish that a token is safe. |
| `start_live_timestamp` | Start live timestamp | UTC — Source event time. Zero means no usable event time, not January 1970. |
| `end_live_timestamp` | End live timestamp | UTC — Source event time. Zero means no usable event time, not January 1970. |
