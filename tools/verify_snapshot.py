"""Verify that the bundled shared integration matches its reviewed manifest."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'docs/runtime-snapshot.json').read_text())
package = root / 'src/omnia_trading'
for name, expected in manifest['paths'].items():
    actual = hashlib.sha256((package / '_engine' / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit('Runtime snapshot mismatch: ' + name)
print('Shared runtime snapshot verified.')
