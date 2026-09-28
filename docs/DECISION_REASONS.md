# Decision reasons

OMNIA answers two separate questions: what the observation supports, and whether
the configured policy permits an action. `decision_notes.explain_observation`
explains the first question and its entry limits without placing an order.

## Input and output

The input is a normalized observation with chain, network, token and pool
identity, timestamp, typed fields and evidence references. The optional policy
objects use `StrategyPolicy` and `Policy`. Pass `now` only when evaluating a
recorded observation at a specified time; otherwise freshness uses the current
clock.

The output schema is `omnia.trading.decision-notes.v1`:

| Field | Meaning |
| --- | --- |
| `observation_id`, `observation_hash` | Identity and content digest of the evaluated observation |
| `notes` | Explanations carrying code, task, level, text, origin, values and evidence |
| `notes_hash` | Digest of the complete notes array |
| `execution_authorized` | Always false for this reporting function |

Levels are `info`, `pass`, `block` and `review`. `pass` applies only to its named
check; it does not authorize a BUY. Native answers supplied through
`native_checks` must be selected by the same observation ID. The caller retains
the inference ledger, model revision and original request for audit.

## Flow and entry

| Code | Condition |
| --- | --- |
| `FLOW_BUY_DOMINANT` | Buys exceed sells |
| `FLOW_SELL_DOMINANT` | Sells exceed buys |
| `FLOW_BALANCED` | Equal, nonzero counts |
| `FLOW_NO_ACTIVITY` | Both counts are zero |
| `FLOW_EVIDENCE_INCOMPLETE` | Missing, invalid or incomparable counts |
| `ENTRY_BUY_SHARE_MET` | Buys / total meets the configured entry minimum |
| `ENTRY_BUY_SHARE_BELOW_MIN` | Insufficient buy share, including zero activity |

Counts must share a source evidence reference, observation timestamp and window.
The default window is 300 seconds. Counts from different windows are not added
together. A rolling-window count increase is not treated as an exact number of
new trades. Volumes and counts remain separate measurements.

## Ownership, risk and market

- Ownership uses `OWNERSHIP_WITHIN_LIMIT`, `OWNERSHIP_ABOVE_MAX` or
  `OWNERSHIP_EVIDENCE_INCOMPLETE`. Holder values need a validated ratio scale.
- Risk uses `RISK_REPORTS_CLEAR`, `RISK_SOURCE_REJECT` or
  `RISK_EVIDENCE_INCOMPLETE`. A valid rejecting flag takes precedence. A missing
  security report does not mean a token passed its security checks.
- Capitalization and liquidity use `MARKET_CAP_*` and `LIQUIDITY_*` with
  `MIN_MET`, `BELOW_MIN` or `USD_UNVERIFIED`. Unknown units cannot pass a USD
  threshold. Numerical values and limits appear together in each note.
- `SOURCE_FIELDS_REQUIRE_REVIEW` records how many supplied fields were eligible
  and how many were quarantined by the validation contract.

## Native model records

`MODEL_ANSWER_UNAVAILABLE`, `MODEL_ANSWER_REQUIRES_REVIEW` and
`MODEL_RULE_DISAGREEMENT` preserve differences between inference and validated
facts. The record includes the original choice, answer probability and acceptance
status. Answer probability is not an independently measured accuracy rate.

Rules do not rewrite a native answer. The report identifies `rule`,
`model_record` and `comparison` origins explicitly. These explanations do not
change strategy execution or extend the native model's output vocabulary.

## Extending the vocabulary

Add a reason only when its condition can be evaluated from a defined input.
For acceleration, require comparable observations from consecutive windows.
For liquidity withdrawal, require pool-reserve observations and their units.
For holder accumulation, require successive holder snapshots. A suggestive
name such as `strong`, `breakout` or `smart_money` is not a substitute for a
condition, threshold and evidence path.
