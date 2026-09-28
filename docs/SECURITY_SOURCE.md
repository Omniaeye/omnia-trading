# Security source adapter

`security_source.adapt_security(raw_bytes, metadata)` projects an archived
`token security` response into a token-scoped observation. It performs no
network calls and is separate from the live collection schedule and strategy.

```python
from omnia_trading.security_source import adapt_security

result = adapt_security(raw_response, {
    'capture_id': capture_id,
    'identity': {
        'chain': chain,
        'network_id': network_id,
        'contract': token_contract,
        'pool': None,
    },
    'requested_at': requested_at,
    'received_at': received_at,
    'sha256': response_sha256,
})
```

The adapter validates SHA-256, request and response identities, transport clocks,
bounded JSON and duplicate keys. Its output includes the original payload,
projected observation, unprojected values with reasons, and unavailable strategy
fields. An empty projection has status `insufficient` and observation `None`.

## Reviewed mappings

| Source fields | Projection | Scope |
|---|---|---|
| `buy_tax`, `sell_tax`, `top_10_holder_rate`, `dev_team_hold_rate`, `creator_balance_rate` | Explicit fraction in [0, 1] | This security endpoint only |
| `is_honeypot` | Boolean or documented `yes`/`no` | BSC within OMNIA's supported networks |
| `renounced_mint`, `renounced_freeze_account` | Strict boolean | Solana only |
| `is_wash_trading` | Strict boolean | Only when returned |

Mappings follow the reviewed OMNIA archive contract in the table above.
The public namespace is `omnia.market.security`; original transport provenance
and response hashes remain in the private capture archive.
Boolean honeypot values also occurred in bounded local CLI captures. The integer
alias `honeypot` is not substituted for a null `is_honeypot`. Ranking's similarly
named tax fields do not inherit this endpoint's fraction contract.

## Fields that remain separate

`can_sell` and `can_not_sell` are not mapped to `sell_simulation_success`:
their response encodings lack a reviewed receipt contract. Zero in both fields
does not establish success or failure. Mint/freeze renunciation does not reveal
the current transfer state or validate a sale route. Additional code-verification
aliases and lock summaries remain in `unprojected_fields` pending review.

An external source's similarly named field requires its own adapter.
[GoPlus `transfer_pausable`](https://docs.gopluslabs.io/reference/response-details)
describes a capability, not current pause state.
[Honeypot.is `simulationSuccess`](https://docs.honeypot.is/ishoneypot)
describes its own check and must retain that source, chain, pair and time.
Neither may be aliased into a current trading receipt without validating scope.

## Integration boundary

Security observations have a null pool because this endpoint queries a token.
Do not copy the ranking's pool into this response. Do not merge a new security
response with an old ranking under one timestamp. A future join must preserve
individual clocks, exact token/network identity and source provenance.

The adapter does not independently verify a provider network namespace on-chain.
It also does not change the strategy's four required risk fields. The generic
risk gate remains incomplete when those fields are unavailable. Chain-specific
security policies need separate validation before replacing that gate.
