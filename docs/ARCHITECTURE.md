# Architecture

Market observation --> Network and contract --> Units and freshness --> Group assessments --> Policy disposition --> Evidence record

## Product and runtime

`contracts.py` validates bounded source input. `pipeline.py` prepares versioned
questions and applies product policy. `_engine` supplies the reviewed local ledger
and Laya adapter; its [snapshot manifest](runtime-snapshot.json) pins exact bytes.
The snapshot is bundled for independent installation, rather than importing an
uninstalled example directory from another checkout.

Laya returns closed typed answers. Deterministic code owns identities, arithmetic,
timestamps, units, thresholds and disposition. Every source string is untrusted
data. A constrained result schema and conservative policy contain what model
output can do; neither source text nor model output can invoke tools.

## Replay and evidence

Identity covers the normalized source packet, question and option order, model
revision, runtime hashes and probability policy. Changes cannot reuse an old
decision under a new identity. Provider errors are recorded by exception type and
remain retryable. Successful records retain their original processing timestamps.

The SQLite WAL ledger serializes one inference at a time per database. Its
transaction prevents duplicate committed records across concurrent callers.
A process failure before commit can repeat inference on replay. There is no
background queue: the caller retains input and schedules retries with backoff.
Separate database files do not provide distributed deduplication.

## Product boundary

The full observation hash covers every supplied field. Each populated catalog group receives a separate assessment. Skipped records retain a source hash and deterministic reason; failed groups are explicit. A candidate never becomes an order in this library.

Probability is evaluated per task and must be calibrated against reviewed data.
The runtime keeps upstream entropy-based confidence separate from maximum answer
probability. Token budgets are checked with the selected tokenizer before inference.
