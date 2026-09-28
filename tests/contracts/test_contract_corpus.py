# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Field contracts preserve unknowns and separate shape from semantic validity."""
import json
from pathlib import Path
import unittest
from omnia_trading.contracts import normalize
from omnia_trading.validation import validate_semantics


class ContractCorpusTests(unittest.TestCase):
    def test_documented_parameter_boundaries(self):
        path = Path(__file__).resolve().parents[1] / 'cases' / 'contracts.jsonl'
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        self.assertTrue(rows)
        self.assertEqual(len({row['id'] for row in rows}), len(rows))
        for row in rows:
            with self.subTest(case=row['id']):
                try:
                    result = 'review' if validate_semantics(normalize(row['input'])) else 'accept'
                except (ValueError, TypeError):
                    result = 'reject'
                self.assertEqual(result, row['expect'], row['purpose'])
