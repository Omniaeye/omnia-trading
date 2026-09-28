# Strategy facts replay

Compare risk flags, flow counts and holder concentration without asking a model
to perform arithmetic or infer missing values. This is a local validation path;
it does not change the strategy, publish results or submit orders.

```python
from datetime import datetime
from omnia_trading.strategy_facts import assess_facts

facts = assess_facts(
    observation,
    now=datetime.fromisoformat(observation['observed_at']),
)
print(facts['checks'])
```

Pass `now` only for an explicit replay. Omit it to validate against the current
clock. `eligible_fields` and `quarantined_fields` preserve the original field
values, units, times and evidence; reasons explain every quarantine.

## Compare recorded inference

```bash
python tools/replay_strategy_facts.py \
  --sample /private/capture/sample.json \
  --expected /private/capture/expected-before-model.json \
  --model-results /private/capture/task-results.jsonl \
  --out-dir /private/replay/run-01
```

The sample is an array of records with an `event` observation. Expected labels
are an array containing `observation_id`, `risk`, `flow` and `ownership`.
Recorded inference is JSONL with `observation_id` and `task_checks`; each task
contains `status` and `answers[task].choice`. Repeat `--model-results` to compare
multiple recorded runs. All inputs must contain the same unique observation IDs.

`summary.json` records coverage, quarantined fields, agreement, model
disagreements and input SHA-256 hashes. `results.jsonl` retains each fact report
or explicit input error. The command performs zero new inference calls.

Keep capture files private. A pool ID's accepted shape does not verify its
protocol, network or on-chain existence. Source adapters must establish these
bindings independently. A complete fact report is not an authorization to trade.

For separate token-security captures, use the [security source adapter](SECURITY_SOURCE.md).
It preserves endpoint-specific encodings and does not merge new security
responses into old market observations.
