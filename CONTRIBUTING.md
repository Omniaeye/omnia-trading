# Contributing

Keep each change scoped to one contract, policy, adapter or regression. Preserve
source evidence and unknown values. Add a failing regression before changing a
decision boundary. Do not publish credentials, customer data or model weights.

```bash
python -m pip install -e . ruff==0.16.8
python -m unittest discover -s tests -v
ruff check src tests tools
python tools/verify_snapshot.py
python -m compileall -q src tests
```

Core contract tests run without model downloads. Record checkpoint, hardware,
input provenance and measured outcomes separately for inference evaluations.
Changes to `_engine` originate in the shared OMNIA Laya integration and require
an explicit snapshot refresh and updated hashes.
