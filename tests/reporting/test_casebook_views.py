# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from omnia_trading.casebook_views import token_groups, write_tokens, curve_svg
from omnia_trading.performance import summarize_quotes


def series(identifier, prices, *, pool=None, chain='solana'):
    points = [{'at': f'2026-09-28T00:{index:02d}:00Z', 'price': price, 'evidence': f'capture:{index}'}
              for index, price in enumerate(prices)]
    return {'id': identifier, 'name': '<token>', 'identity': {'chain': chain, 'network_id': chain,
            'contract': 'contract', 'pool': pool}, 'points': points, 'performance': summarize_quotes(points)}


class CasebookViewsTests(unittest.TestCase):
    def test_unique_identity_preserves_pools_and_networks(self):
        rows = [series('a', [1, 2]), series('b', [2, 1], pool='other'), series('c', [1, 1], chain='bsc')]
        groups = token_groups(rows)
        self.assertEqual(len(groups), 2)
        self.assertEqual(sorted(len(group['series']) for group in groups), [1, 2])

    def test_curves_and_indexes_include_declines_single_quotes_and_empty_series(self):
        rows = [series('a', [10, 2, 4]), series('b', [1], pool='second'), series('c', [], chain='bsc')]
        original = deepcopy(rows)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            groups = write_tokens(root, rows, [])
            index = (root / 'tokens/README.md').read_text(encoding='utf-8')
            for group in groups:
                self.assertIn(group['id'], index)
            detail = (root / 'tokens' / (next(g['id'] for g in groups if g['identity']['chain'] == 'solana') + '.md')).read_text()
            self.assertIn('-60.00%', detail)
            self.assertIn('80.00%', detail)
            self.assertEqual((root / 'tokens/a.svg').read_text().count('<circle '), 3)
            self.assertFalse((root / 'tokens/c.svg').exists())
        self.assertEqual(rows, original)

    def test_svg_escapes_source_names_and_uses_real_time_spacing(self):
        row = series('a', [1, 2, 1])
        row['points'][1]['at'] = '2026-09-28T00:00:01Z'
        svg = curve_svg(row)
        self.assertIn('&lt;token&gt;', svg)
        self.assertIn('65.667,', svg)
        self.assertNotIn('<token>', svg)
