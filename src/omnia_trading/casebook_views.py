# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Contract indexes and full quote curves for a frozen market window."""

from collections import Counter
import hashlib
import html
import json

from .contracts import timestamp
from ._engine.ledger import digest


def text(value):
    return html.escape(str(value), quote=True).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ').replace('`', '&#96;')


def token_groups(rows):
    """Pools stay separate; identity never depends on a ticker or price outcome."""
    groups = {}
    for row in rows:
        identity = {key: row['identity'][key] for key in ('chain', 'network_id', 'contract')}
        key = json.dumps(identity, sort_keys=True)
        item = groups.setdefault(key, {'id': hashlib.sha256(key.encode()).hexdigest()[:24], 'identity': identity,
                                     'name': row['name'], 'series': []})
        item['series'].append(row)
    return sorted(groups.values(), key=lambda item: (item['identity']['chain'], item['name'].casefold(), item['id']))


def curve_svg(row):
    """Plot every recorded quote against elapsed time, with a visible 1x baseline."""
    points = sorted(row['points'], key=lambda point: timestamp(point['at']))
    if not points:
        return None
    start = timestamp(points[0]['at'])
    duration = max((timestamp(points[-1]['at']) - start).total_seconds(), 1)
    values = [point['price'] / points[0]['price'] for point in points]
    lower, upper = min(values + [1]), max(values + [1])
    padding = max((upper - lower) * .08, .05)
    lower, upper = max(0, lower - padding), upper + padding

    def y(value):
        return 220 - (value - lower) / (upper - lower) * 180

    coords = [(60 + (timestamp(point['at']) - start).total_seconds() / duration * 680, y(value))
              for point, value in zip(points, values)]
    path = ' '.join(f'{x:.3f},{v:.3f}' for x, v in coords)
    color = '#087f6d' if values[-1] >= 1 else '#b33b47'
    label = text(f"{row['name']}: {len(points)} observed quotes; each price relative to the first quote")
    return '\n'.join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 270" role="img">',
        f'<title>{label}</title>', '<rect width="800" height="270" rx="12" fill="#f6f8fa"/>',
        '<g font-family="sans-serif" font-size="12" fill="#334155">',
        f'<text x="60" y="24">{label}</text>',
        f'<text x="8" y="48">{upper:.2f}x</text><text x="8" y="220">{lower:.2f}x</text>',
        f'<line x1="60" y1="{y(1):.3f}" x2="740" y2="{y(1):.3f}" stroke="#94a3b8" stroke-dasharray="4 4"/>',
        f'<text x="744" y="{y(1):.3f}">1x</text>',
        f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{path}"/>',
        *[f'<circle cx="{x:.3f}" cy="{v:.3f}" r="2" fill="{color}"/>' for x, v in coords],
        f'<text x="60" y="250">{text(points[0]["at"])}</text>',
        f'<text x="740" y="250" text-anchor="end">{text(points[-1]["at"])}</text>',
        '</g></svg>', '',
    ])


def write_tokens(output, rows, observations):
    groups = token_groups(rows)
    folder = output / 'tokens'
    folder.mkdir(exist_ok=True)
    table = ['# All tokens', '', '[Market window](../README.md)', '',
             'One entry per network and contract. Pools retain independent curves. Alphabetical order; no return filter.', '',
             '| Token | Network | Contract | Series | Quotes | Native assessments | Policy events |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for group in groups:
        identity = group['identity']
        selected = [item for item in observations if all(item['event']['identity'][k] == v for k, v in identity.items())]
        actions = Counter(event['action'] for row in group['series']
                          for event in (row['performance']['scenario'] or {}).get('events', []))
        count = sum(len(row['points']) for row in group['series'])
        table.append(f"| [{text(group['name'])}]({group['id']}.md) | {identity['chain']} | `{identity['contract']}` | "
                     f"{len(group['series'])} | {count} | {len(selected)} | {sum(actions.values())} |")
        lines = [f"# {text(group['name']).strip()}", '', f"**{identity['chain']}** / `{identity['contract']}`", '',
                 '[All tokens](README.md) · [Market window](../README.md)', '',
                 '## Native assessments', '']
        for item in selected:
            identifier = digest(item['event']['id'])[:16]
            lines.append(f"- [{text(item['event']['observed_at'])}](../cases/{identifier}.md): source parameters and model answers.")
        if not selected:
            lines.append('This contract is in the quote cohort; it has no native model assessment in this window.')
        for row in sorted(group['series'], key=lambda value: value['id']):
            series_id = row['id']
            points = sorted(row['points'], key=lambda point: timestamp(point['at']))
            lines += ['', f"## Series {series_id}", '', f"Pool: `{text(row['identity'].get('pool') or 'not supplied')}`", '',
                      f"[Complete series](../series/{identity['chain']}/{series_id}.json)", '']
            chart = curve_svg(row)
            if chart:
                (folder / f'{series_id}.svg').write_text(chart, encoding='utf-8', newline='\n')
                lines += [f'![Observed quote curve]({series_id}.svg)', '',
                          'Every dot is a captured quote. Lines connect observations; the curve ends at the last available quote.', '']
            market = row['performance']['market']
            if market:
                lines += ['| Peak | Final | Return | Maximum drawdown |', '| ---: | ---: | ---: | ---: |',
                          f"| {market['peak_multiple']:.4f}x | {market['final_multiple']:.4f}x | "
                          f"{market['return_ratio']:+.2%} | {market['max_drawdown_ratio']:.2%} |", '']
            else:
                lines += ['Fewer than two quotes: return and drawdown are not calculated.', '']
            lines += ['### Complete quote timeline', '', '| Time (UTC) | Price (USD) | Multiple | Evidence |',
                      '| --- | ---: | ---: | --- |']
            for point in points:
                lines.append(f"| {text(point['at'])} | {point['price']:.12g} | {point['price'] / points[0]['price']:.4f}x | `{text(point['evidence'])}` |")
            lines += ['', '### Exit-policy timeline', '',
                      'Calculated from captured quotes under the window policy. Native assessments are linked separately above.', '',
                      '| Time (UTC) | Action | Price (USD) | Evidence |', '| --- | --- | ---: | --- |']
            for event in (row['performance']['scenario'] or {}).get('events', []):
                lines.append(f"| {text(event['at'])} | {event['action']} | {event['price']:.12g} | `{text(event['evidence'])}` |")
        (folder / (group['id'] + '.md')).write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    (folder / 'README.md').write_text('\n'.join(table) + '\n', encoding='utf-8', newline='\n')
    by_series = {row['id']: group['id'] for group in groups for row in group['series']}
    for chain in ('robinhood', 'bsc', 'solana'):
        target = output / 'series' / chain
        target.mkdir(parents=True, exist_ok=True)
        lines = [f'# {chain.upper()} quote series', '', '[All tokens](../../tokens/README.md) | [Market window](../../README.md)', '',
                 'Every series, ordered by token name. Pools and contracts retain separate identities.', '',
                 '| Token | Contract | Quotes | Peak | Final | Drawdown | Curve and timeline |',
                 '| --- | --- | ---: | ---: | ---: | ---: | --- |']
        for row in sorted((r for r in rows if r['identity']['chain'] == chain), key=lambda r: (r['name'].casefold(), r['id'])):
            market = row['performance']['market']
            peak = f"{market['peak_multiple']:.3f}x" if market else 'N/A'
            final = f"{market['final_multiple']:.3f}x" if market else 'N/A'
            drawdown = f"{market['max_drawdown_ratio']:.2%}" if market else 'N/A'
            lines.append(f"| {text(row['name'])} | `{row['identity']['contract']}` | {len(row['points'])} | {peak} | {final} | "
                         f"{drawdown} | [Inspect](../../tokens/{by_series[row['id']]}.md) |")
        (target / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    return groups
