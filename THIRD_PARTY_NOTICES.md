# Attribution

OMNIA Trading is original integration software maintained by OMNIA EYE.
Original public source is copyright 2026 OMNIA EYE Corporation, Apache-2.0.

The `_engine` package is a byte-for-byte snapshot of OMNIA's own ledger and local
adapter from [omnia-laya](https://github.com/Omniaeye/omnia-laya/tree/256eaf39550291dec7378d5a20078cc0d500e852/examples/omnia).
[The snapshot manifest](docs/runtime-snapshot.json) pins its revision and hashes.
Vendoring keeps the wheel self-contained while both products share the same
reviewed implementation. Refresh it explicitly; do not edit duplicated engine files.

Optional inference uses [Laya](https://github.com/NandhaKishorM/laya), originally
maintained by Convai Innovations under Apache-2.0. Model weights are distributed
by their publishers and retain their own licenses. This repository does not claim
authorship of the Laya model or endorsement by its authors or TypeSafe AI.

See [LICENSE](LICENSE) for the public source license.
