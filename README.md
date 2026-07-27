<p align="center"><img src="assets/eye.png" width="112" alt="OMNIA EYE" /></p>
<h1 align="center">OMNIA TRADING</h1>
<p align="center"><strong>Source observations. Explicit checks. Traceable assessments.</strong></p>
<p align="center">JEV decision integration · Evidence-first infrastructure</p>
<p align="center"><a href="#quickstart">Quickstart</a> · <a href="docs/API.md">API</a> · <a href="docs/PARAMETERS.md">Parameters</a> · <a href="docs/OPERATIONS.md">Operations</a></p>
<p align="center"><a href=".github/workflows/checks.yml"><img alt="Product checks" src="https://github.com/Omniaeye/omnia-trading/actions/workflows/checks.yml/badge.svg" /></a></p>

---

Turn a source observation into an inspectable data-quality assessment. OMNIA Trading validates asset identity, field semantics, units, windows and freshness; assesses bounded groups with a local typed model; and stores the final policy result with its evidence references.

The package supports **102 optional input definitions**. This is the adapter contract, not a claim that a provider supplies every field. Missing optional fields do not imply zero, safety, or collection coverage.

| Family | Definitions | Examples |
| --- | ---: | --- |
| Market | 28 | Price, market cap, liquidity, supply, side volumes and explicit windows |
| Holders | 17 | Counts, concentration, creator balance and source-tagged exposure |
| Risk | 19 | Taxes, source flags, authority addresses and reported simulation results |
| Lifecycle | 17 | Event times, launch state, creator, block number and slot |
| Social | 21 | Source-linked profiles, attention, follower count and status fields |
| **Total** | **102** | **[Executable parameter catalog](docs/PARAMETERS.md)** |

## Decision path

```text
Source observation -> Identity and shape -> Field semantics and policy
                   -> Bounded model assessments -> Freshness recheck
                   -> Durable final assessment
```

Supported network families are **Robinhood Chain, BSC and Solana**. Identity includes an explicit network identifier, contract or mint, and optional pool. EVM addresses are normalized; Solana addresses preserve case and must decode to 32 bytes. The adapter owns network-ID binding and source provenance. The library performs no RPC lookup or affiliation verification.

Every field carries a value, unit, window, observation time and evidence reference. Unknown or semantically invalid supplied values remain visible and require review. A negative holder count, ambiguous currency, missing aggregate window, invalid creator address or zero event timestamp cannot be promoted by a confident model answer.

## Policy and interpretation

Defaults require market cap of at least **USD 30,000**, liquidity of at least **USD 10,000**, an explicit honeypot boolean, and observations no older than **120 seconds**. The age and monetary thresholds are configurable. No optional field is treated as required merely because it appears in the catalog.

| Disposition | Meaning |
| --- | --- |
| `candidate` | Deterministic checks passed and every supplied batch received an accepted `usable` answer |
| `review` | Missing, ambiguous, stale, inconsistent or unassessed evidence needs attention |
| `skip` | A well-formed market value is below policy or the source reports a honeypot |

A rejecting condition takes precedence conservatively; all other detected reasons remain in the record. For example, stale low liquidity produces `skip` with both the freshness and threshold reasons. A false honeypot flag alone never establishes safety.

`candidate` is a data-policy outcome. It is not an investment recommendation, buy signal, security certification, or execution permission. Every assessment carries **`execution_authorized: false`**. Collection, strategy, position limits, transaction simulation, signing and execution remain outside this package.

## Bounded assessments

Each populated family is partitioned into stable batches of at most **four fields**. Every supplied field appears once in `assessment_batches`; split groups use keys such as `Market:part1`. Small groups retain `Market`, `Risk`, and the other family names.

The two-field Market plus one-field Risk example plans two model assessments. The union of all 102 definitions plans 28, although some definitions apply to different chains and should not be supplied together as valid input. Cache hits reuse answers. Long field values can still exceed the selected checkpoint's token budget: the affected batch is explicitly failed and the final result requires review. There is no silent truncation or guarantee that arbitrary content fits the default 512-token checkpoint.

## Descriptive metrics

The package can derive `buy_share`, `net_buy_volume`, `liquidity_to_market_cap` and `circulating_supply_fraction` when their required inputs have compatible units and the same source evidence, observation time and window. Denominators must be positive. Each metric retains its formula and input references.

These are calculations over reported aggregates. A rolling buy count changing from 100 to 180 does not prove 80 individually identified trades. Quote reserves, reported price impact and sell-simulation flags do not establish an executable price or a real fill.

## Quickstart

Python 3.10 or newer. Inspect contracts without installing model dependencies:

```bash
python -m pip install .
omnia-trading --catalog
```

For local inference, install the pinned runtime and set the reviewed English checkpoint revision:

```bash
git clone https://github.com/Omniaeye/omnia-trading.git
cd omnia-trading
python -m pip install '.[local]'
export OMNIA_LAYA_REVISION=55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851
omnia-trading --input examples/input.jsonl
```

PowerShell:

```powershell
python -m pip install '.[local]'
$env:OMNIA_LAYA_REVISION = '55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851'
omnia-trading --input examples/input.jsonl
```

The included observation is a dated contract example. Ordinary replay applies current-time freshness and therefore requires review once it expires. Use your adapter's fresh observations for current assessment; use the Python API's explicit `now` only for intentional historical replay.

At a clean batch limit, the CLI emits a paused boundary with `next_offset_bytes` for files. Resume the same immutable input using the returned byte offset:

```bash
omnia-trading --input observations.jsonl --offset-bytes 12345
```

See [Operations](docs/OPERATIONS.md) for configuration, output boundaries, failure recovery and storage ownership.

## Inspect and verify

Final `candidate`, `review` and `skip` outcomes are persisted separately from model-answer cache records. Each includes an assessment ID, observation hash, source and evidence references, policy configuration, catalog fingerprint, evaluation clock, expiry, batch coverage and explicit failures. An old cached answer can participate in a new, time-dependent policy assessment. Source archives remain caller-owned.

```bash
python -m pip install -e . ruff==0.16.8
python -m unittest discover -s tests -v
ruff check src tests tools
python tools/verify_snapshot.py
```

Contract and recovery tests establish implementation behavior. They do not establish task accuracy, investment performance, throughput or production readiness. Task-specific calibration and reviewed source datasets remain necessary; see [Validation](docs/VALIDATION.md).

| Documentation | Purpose |
| --- | --- |
| [API](docs/API.md) | Input, output, replay and integration examples |
| [Parameters](docs/PARAMETERS.md) | Types, units, bounds, windows and chain applicability |
| [Architecture](docs/ARCHITECTURE.md) | Deterministic checks, model batches and durable evidence |
| [Operations](docs/OPERATIONS.md) | Configuration, recovery, concurrency and deployment limits |
| [Research](docs/RESEARCH.md) | Primary sources and their evidential limits |

The product code is original OMNIA work. [OMNIA Laya](https://github.com/Omniaeye/omnia-laya) supplies the attributed local decision integration; [the multichain evidence field](https://github.com/Omniaeye/data-stream-multichain) is a related source project, not an embedded live collector.

[Apache-2.0](LICENSE) · [Notices](THIRD_PARTY_NOTICES.md) · [Security](SECURITY.md)
