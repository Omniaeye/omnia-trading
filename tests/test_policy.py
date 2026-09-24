from datetime import datetime, timedelta, timezone
import unittest
from helpers import event
from omnia_trading.policy import Policy, evaluate


class PolicyTests(unittest.TestCase):
    def test_values_in_wrong_currency_are_not_usd(self):
        item = event()
        item['fields']['market_cap']['unit'] = 'source_denomination'
        result, reasons = evaluate(item, Policy())
        self.assertEqual(result, 'review')
        self.assertIn('missing_usd_value:market_cap', reasons)

    def test_missing_flags_and_string_false_are_unknown(self):
        for value in (None, 'false', 0):
            item = event()
            item['fields']['is_honeypot']['value'] = value
            self.assertEqual(evaluate(item, Policy())[0], 'review')

    def test_source_reported_risk_is_skip(self):
        item = event()
        item['fields']['is_honeypot']['value'] = True
        self.assertEqual(evaluate(item, Policy())[0], 'skip')

    def test_stale_and_future_fields_require_review(self):
        for seconds in (-600, 600):
            item = event()
            item['fields']['liquidity']['observed_at'] = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
            self.assertEqual(evaluate(item, Policy())[0], 'review')

    def test_market_cap_gate(self):
        item = event()
        item['fields']['market_cap']['value'] = 29999
        self.assertEqual(evaluate(item, Policy())[0], 'skip')

    def test_stale_envelope_with_fresh_fields_requires_review(self):
        item = event()
        item['observed_at'] = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        result, reasons = evaluate(item, Policy())
        self.assertEqual(result, 'review')
        self.assertIn('stale_or_future:observation', reasons)

    def test_invalid_policy(self):
        for value in (-1, float('nan'), True):
            with self.assertRaises(ValueError):
                Policy(min_market_cap_usd=value)
