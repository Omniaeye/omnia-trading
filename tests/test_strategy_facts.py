# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Source-bound strategy facts must not depend on model confidence."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import unittest

from omnia_trading.identity import identity
from omnia_trading.contracts import timestamp
from omnia_trading.strategy_facts import assess_facts


class StrategyFactsTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'examples/strategy.jsonl'
        self.event = json.loads(path.read_text())['observation']
        self.now = timestamp(self.event['observed_at'])

    def assess(self):
        return assess_facts(self.event, now=self.now)

    def test_bytes32_pool_is_not_a_token_address(self):
        value = {**self.event['identity'], 'pool': '0x' + 'AB' * 32}
        self.assertEqual(identity(value)['pool'], '0x' + 'ab' * 32)
        with self.assertRaises(ValueError):
            identity({**value, 'contract': value['pool']})
        with self.assertRaises(ValueError):
            identity({**value, 'pool': '0x' + 'ab' * 31})

    def test_missing_risk_does_not_become_clear(self):
        del self.event['fields']['sell_simulation_success']
        risk = self.assess()['checks']['risk']
        self.assertEqual(risk['choice'], 'unknown')
        self.assertIn('missing_field:sell_simulation_success', risk['reasons'])

    def test_explicit_risk_rejects_even_with_another_missing_report(self):
        self.event['fields']['is_honeypot']['value'] = True
        del self.event['fields']['sell_simulation_success']
        self.assertEqual(self.assess()['checks']['risk']['choice'], 'reject')

    def test_numeric_direction_and_entry_threshold_are_separate(self):
        self.event['fields']['buys']['value'] = 55
        self.event['fields']['sells']['value'] = 45
        flow = self.assess()['checks']['flow']
        self.assertEqual(flow['choice'], 'supportive')
        self.assertFalse(flow['entry_threshold_met'])
        self.assertAlmostEqual(flow['buy_share'], .55)

    def test_sell_majority_is_weak(self):
        self.event['fields']['buys']['value'] = 12
        self.event['fields']['sells']['value'] = 22
        self.assertEqual(self.assess()['checks']['flow']['choice'], 'weak')

    def test_unaligned_captures_are_unknown(self):
        for attribute, value in [('window_seconds', 3600), ('evidence', 'capture:other')]:
            with self.subTest(attribute=attribute):
                original = deepcopy(self.event)
                self.event['fields']['sells'][attribute] = value
                self.assertEqual(self.assess()['checks']['flow']['choice'], 'unknown')
                self.event = original

    def test_zero_counts_have_no_buy_share(self):
        for key in ('buys', 'sells'):
            self.event['fields'][key]['value'] = 0
        result = self.assess()['checks']['flow']
        self.assertEqual(result['choice'], 'weak')
        self.assertIsNone(result['buy_share'])
        self.assertFalse(result['entry_threshold_met'])

    def test_percent_normalization_preserves_input(self):
        self.event['fields']['top_10_holder_rate'].update(value=80.65, unit='percent')
        before = deepcopy(self.event)
        result = self.assess()['checks']['ownership']
        self.assertEqual(result['choice'], 'concentrated')
        self.assertAlmostEqual(result['ratio'], .8065)
        self.assertEqual(self.event, before)

    def test_ambiguous_unit_is_quarantined_not_converted(self):
        self.event['fields']['top_10_holder_rate']['unit'] = 'source_scale'
        result = self.assess()
        self.assertEqual(result['checks']['ownership']['choice'], 'unknown')
        self.assertIn('top_10_holder_rate', result['quarantined_fields'])

    def test_stale_data_is_unknown(self):
        self.now += timedelta(minutes=10)
        self.assertTrue(all(row['choice'] == 'unknown' for row in self.assess()['checks'].values()))

    def test_boolean_code_is_not_a_verified_boolean(self):
        self.event['fields']['is_honeypot'].update(value=0, unit='source_scale')
        self.assertEqual(self.assess()['checks']['risk']['choice'], 'unknown')

    def test_result_cannot_authorize_execution(self):
        result = self.assess()
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(result['engine'], 'deterministic')
        self.assertNotIn('action', result)
        self.assertEqual(set(result['eligible_fields']) | set(result['quarantined_fields']), set(self.event['fields']))


if __name__ == '__main__':
    unittest.main()
