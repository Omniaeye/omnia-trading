# Operations

## Install and configure

Use the commands in [Quickstart](../README.md#quickstart). `.env.example` documents
consumed variables; export them in the process environment. No dotenv file is
loaded automatically. `OMNIA_LAYA_REVISION` must be a reviewed immutable 40-character
checkpoint SHA. An empty revision fails before processing.

| Setting | Purpose |
| --- | --- |
| `OMNIA_LAYA_MODEL` | Explicit checkpoint family: english, typed-decisions or multilingual |
| `OMNIA_LAYA_DEVICE` | cpu, cuda or mps |
| `OMNIA_LAYA_THREADS` | CPU inference threads, default 2 |
| `OMNIA_LAYA_MAX_LEN` | Full context budget, within the selected model's supported limit |
| `OMNIA_LAYA_HEAD_MAX_LEN` | Question and criteria budget |
| `OMNIA_LAYA_MAX_INPUT_BYTES` | Per-record byte bound, default 65536 |
| `OMNIA_LAYA_MIN_PROBABILITY` | Minimum answer probability, default 0.8 |
| `OMNIA_TRADING_DATABASE` | Private SQLite ledger path |
| `OMNIA_TRADING_MAX_RECORDS` | Maximum input lines per invocation, default 1000 |

Trading also consumes MAX_AGE_SECONDS, MIN_MARKET_CAP_USD and MIN_LIQUIDITY_USD with the OMNIA_TRADING_ prefix; defaults are 120, 30000 and 10000.

## Failures and recovery

The CLI emits one JSON result per processed nonempty line. Invalid UTF-8, malformed
JSON, contract failures and oversized lines emit a typed failure and processing
continues. At the invocation record limit it emits `RECORD_LIMIT` and stops reading;
retain the original input and resume from that boundary. Blank lines consume the
line budget. `0` means the invocation completed, `1` means record errors or limit,
and `2` means startup failure. Review is a completed decision, not a process error.

Replaying unchanged records uses persistent cache; failed inference can be retried.
Back up the SQLite database consistently using SQLite's backup API, not a live copy
of the main file without its WAL. Close the process before moving the database.
Keep input archives, output and ledger paths distinct. Database size and retention
are operator-owned; this CLI performs no automatic deletion.

## Runtime ownership

Keep one active worker per ledger for predictable latency. Scale independent
partitions only when duplicate ownership is explicit. Measure real queue age,
inference latency, review rate and error rate in the application scheduler.
Use a private model cache; after downloading the selected checkpoint, set
`HF_HUB_OFFLINE=1` to prohibit new Hub requests. Do not expose a public API around
this CLI without separate authentication, budgets and request limits.
