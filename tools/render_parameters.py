# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Render operator documentation from the same catalog used by validation."""
from pathlib import Path
import json


def render(root):
    rows = json.loads((root / 'src/omnia_trading/parameters.json').read_text(encoding='utf-8'))
    out = ['# Parameter catalog', '',
           f'{len(rows)} executable input definitions across Market, Holders, Risk, Lifecycle and Social.', '',
           'Each supplied field retains its value, unit, window, observation time and evidence reference. '
           'The catalog defines accepted adapter inputs. Optional absence is allowed; supplied null values '
           'require review. Collection coverage is established separately by the adapter.', '',
           'Run `omnia-trading --catalog` for the machine-readable schema and fingerprint. '
           'This page is generated with `python tools/render_parameters.py` from that same catalog.', '',
           '## Reading the contract', '',
           '- Units are case-sensitive accepted spellings; monetary policy uses `USD`.',
           '- Proportion bounds below are expressed as ratios. `50 percent` corresponds to `0.5 ratio`.',
           '- A snapshot requires a null window. An aggregate requires an explicit window.',
           '- Event times use timezone-aware `UTC` text or declared Unix seconds/milliseconds.',
           '- Values outside a domain remain source evidence but prevent automatic promotion.',
           '- Addresses are checked against the declared network family.', '',
           'See [API](API.md) for envelope shape, review reasons, derived metrics and examples.']
    for group in ('Market', 'Holders', 'Risk', 'Lifecycle', 'Social'):
        fields = [r for r in rows if r['group'] == group]
        out += ['', f'## {group} — {len(fields)} fields', '',
                '| Parameter | Type | Units | Domain | Window | Networks |',
                '|---|---|---|---|---|---|']
        for row in fields:
            bounds = ', '.join(label + str(row[key]) for label, key in [('min ', 'minimum'), ('max ', 'maximum')]
                               if row[key] is not None) or 'type constrained'
            window = (str(row['window_seconds']) + ' s' if row['window_seconds'] else 'explicit aggregate window') \
                if row['requires_window'] else 'snapshot / null'
            units = ', '.join('`' + u + '`' for u in row['allowed_units'])
            out.append(f"| `{row['key']}` | {row['kind']} | {units} | {bounds} | {window} | {', '.join(row['chains'])} |")
        out += ['', '### Meaning and evidence', '']
        for row in fields:
            out += [f"**`{row['key']}` — {row['label']}**", '', row['description'], '',
                    row['note'], f"Missingness: `{row['missing_rule']}`.", '']
    return '\n'.join(out).rstrip() + '\n'


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    (root / 'docs/PARAMETERS.md').write_text(render(root), encoding='utf-8', newline='\n')
