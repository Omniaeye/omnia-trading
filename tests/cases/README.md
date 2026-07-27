# Contract vectors

`contracts.jsonl` is a versioned corpus of input-boundary examples. Every row has
an identifier, a specific validation purpose, a complete input and an expected
contract disposition. The corpus runner executes all rows in the unit suite.

`accept` means the input satisfies the examined contract. `reject` means its
shape or required identity is invalid. Trading additionally uses `review` when
a structurally valid field has unknown or incompatible semantics.

These labels describe deterministic contracts. They are not human judgments of
news relevance, investment decisions, observed market activity or model accuracy.
No model is called by this corpus. Separate labeled evaluation is required to
measure precision, coverage and calibration of inference.
