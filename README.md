<p align="center"><img src="assets/eye.png" width="112" alt="OMNIA EYE" /></p>
<h1 align="center">OMNIA TRADING</h1>
<p align="center"><strong>Every parameter. One traceable assessment.</strong></p>
<p align="center">JEV decision integration · Evidence-first infrastructure</p>
<p align="center"><a href="#quickstart">Quickstart</a> · <a href="docs/API.md">API</a> · <a href="docs/ARCHITECTURE.md">Architecture</a> · <a href="docs/OPERATIONS.md">Operations</a> · <a href="docs/RESEARCH.md">Research</a></p>
<p align="center"><a href=".github/workflows/checks.yml"><img alt="Product checks" src="https://github.com/Omniaeye/omnia-trading/actions/workflows/checks.yml/badge.svg" /></a> <a href="LICENSE"><img alt="Apache-2.0" src="https://img.shields.io/badge/license-Apache_2.0-63d6bc" /></a></p>

---

Connect market observations to an inspectable decision record. Identify the network and contract, preserve every parameter, evaluate the available evidence and keep policy checks separate from model answers.

| Parameter family | Definitions | Examples |
| --- | ---: | --- |
| Market | 19 | Price, market cap, liquidity, volume, buys, sells and windows |
| Holders | 13 | Holder count, concentration, creator exposure and participant metrics |
| Risk | 15 | Source-reported taxes, permissions, honeypot, burns and locks |
| Lifecycle | 15 | Creation times, pool stage, launch platform, creator and migration |
| Social | 20 | Profiles, website, Telegram, attention and source-status fields |
| **Total** | **82** | **[Full parameter catalog](docs/PARAMETERS.md)** |

Each observation declares its actual fields. A catalog definition does not imply
that every source supplies it for every token.


## Decision path

```text
Market observation --> Network and contract --> Units and freshness --> Group assessments --> Policy disposition --> Evidence record
```

## Identity before interpretation

Supported network families: **Robinhood Chain, BSC and Solana**. Every input carries
an explicit network identifier, contract or mint, and optional pool. EVM addresses
are normalized; Solana addresses preserve case and are checked as 32-byte Base58
values. A ticker never merges two assets. The source adapter owns network-ID binding;
the library performs no RPC lookup or chain-discovery request.

Each datapoint carries its value, unit, window, observation time and evidence ID.
Unknowns stay unknown. A rolling buy count moving from 100 to 180 is a change in
an aggregate, not proof of 80 individually identified trades.

## Policy controls the boundary

Default checks require a USD market cap of at least 30,000, USD liquidity of at least
10,000 and observations no older than 120 seconds. All three are configurable.
Missing or ambiguous inputs require review. A source-reported honeypot flag triggers
`skip`; a false flag alone is not a security guarantee.

Every populated parameter group receives a separate bounded assessment. A group
that exceeds the selected checkpoint budget produces an explicit failure for review;
content is not silently shortened. See [decision flow](docs/ARCHITECTURE.md).

| Disposition | Meaning |
| --- | --- |
| `candidate` | Configured data checks passed and all supplied groups were assessed as usable |
| `review` | Missing, stale, inconsistent or uncertain evidence needs attention |
| `skip` | A deterministic market or reported-risk condition rejects this observation |

`candidate` is a data-policy result, not a buy signal. Records carry
`execution_authorized: false`. Signing, order placement and risk authorization
belong to a separate executor; this package receives no wallet keys.


## Quickstart

Python 3.10 or newer. Install the product and its pinned local inference dependency:

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

Install with `python -m pip install .` when consuming contracts without local
inference. The optional runtime loads only when an item needs model evaluation.
Repeated identical requests reuse recorded decisions. The included input is a
small contract example; replace it with source observations from your adapter.
The Trading example uses a dated observation, so freshness checks will require review when it is replayed later.

## Inspect every decision

Each model record includes source and evidence IDs, input and question fingerprints,
the pinned checkpoint, runtime source hashes, model answers, probability gates,
processing time and cache status. Raw input text is not persisted in that ledger.
Keep source archives separately and protect the ledger as application data.

| Read next | Purpose |
| --- | --- |
| [API](docs/API.md) | Input fields, output semantics and callable interface |
| [Architecture](docs/ARCHITECTURE.md) | Deterministic checks, model boundary and replay |
| [Operations](docs/OPERATIONS.md) | Environment, limits, failures and recovery |
| [Validation](docs/VALIDATION.md) | Executed checks and inference evidence |
| [Research](docs/RESEARCH.md) | Primary sources behind the design |

## Build and verify

```bash
python -m pip install -e . ruff==0.16.8
python -m unittest discover -s tests -v
ruff check src tests tools
python tools/verify_snapshot.py
```

Both products share the reviewed [OMNIA Laya](https://github.com/Omniaeye/omnia-laya)
integration and connect to the [multichain evidence field](https://github.com/Omniaeye/data-stream-multichain).
The product code is original OMNIA work. Laya remains the attributed local decision
engine. [Apache-2.0](LICENSE) · [Notices](THIRD_PARTY_NOTICES.md) · [Security](SECURITY.md)
