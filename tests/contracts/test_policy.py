# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from tests.helpers import event
from omnia_trading.policy import Policy, evaluate
from omnia_trading.config import Config


class PolicyTests(unittest.TestCase):
    def test_values_in_wrong_currency_are_not_usd(self):
        item = event()
        item['fields']['market_cap']['unit'] = 'source_denomination'
        result, reasons = evaluate(item, Policy())
        self.assertEqual(result, 'review')
        self.assertIn('missing_usd_value:market_cap', reasons)

    def test_invalid_flags_are_not_optional_absence(self):
        for value in ('false', 0):
            item = event()
            item['fields']['is_honeypot']['value'] = value
            self.assertEqual(evaluate(item, Policy())[0], 'review')

    def test_null_optional_flag_and_strict_requirement(self):
        item = event()
        item['fields']['is_honeypot']['value'] = None
        self.assertEqual(evaluate(item, Policy())[0], 'observe')
        self.assertEqual(evaluate(item, Policy(require_honeypot_report=True))[0], 'review')

    def test_optional_market_values_are_checked_when_reported(self):
        item = event()
        del item['fields']['liquidity']
        self.assertEqual(evaluate(item, Policy())[0], 'observe')
        self.assertEqual(evaluate(item, Policy(require_liquidity=True))[0], 'review')

    def test_policy_requirements_are_booleans(self):
        for key in ('require_market_cap', 'require_liquidity', 'require_honeypot_report'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                Policy(**{key: 'false'})

    def test_environment_requirements_are_explicit_and_validated(self):
        with patch.dict('os.environ', {'OMNIA_LAYA_REVISION': 'a' * 40, 'OMNIA_TRADING_REQUIRE_LIQUIDITY': 'true'}):
            self.assertTrue(Config.from_env().policy().require_liquidity)
        with patch.dict('os.environ', {'OMNIA_LAYA_REVISION': 'a' * 40, 'OMNIA_TRADING_REQUIRE_LIQUIDITY': 'maybe'}):
            with self.assertRaises(ValueError):
                Config.from_env()

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
