# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts exercise policy independently of model quality."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import patch

from helpers import Backend, datapoint, event
from omnia_trading._engine.ledger import DecisionLedger
from omnia_trading.catalog import PARAMETERS
from omnia_trading.config import Config
from omnia_trading.contracts import normalize
from omnia_trading.features import derive_metrics
from omnia_trading.pipeline import process
from omnia_trading.validation import validate_semantics


NOW = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)


def point(value, unit='USD', window=None):
    result = datapoint(value, unit, window=window)
    result['observed_at'] = NOW.isoformat()
    return result


def observation():
    result = event()
    result['observed_at'] = NOW.isoformat()
    for field in result['fields'].values():
        field['observed_at'] = NOW.isoformat()
    return result


def full_catalog_observation():
    result = observation()
    for definition in PARAMETERS:
        kind = definition['kind']
        value = {'number': .5, 'integer': 1, 'boolean': False, 'text': 'source-reported',
                 'address': result['identity']['contract'], 'timestamp': NOW.isoformat()}[kind]
        window = (definition['window_seconds'] or 60) if definition['requires_window'] else None
        result['fields'][definition['key']] = point(value, definition['allowed_units'][0], window)
    result['fields']['market_cap'] = point(50000)
    result['fields']['liquidity'] = point(20000)
    # This union intentionally includes chain-specific fields. It tests complete coverage,
    # not the existence of a chain on which every catalog field is simultaneously applicable.
    return result


class TradingHardeningTests(unittest.TestCase):
    def setUp(self):
        self.ledger = DecisionLedger(':memory:')

    def tearDown(self):
        self.ledger.close()

    def test_usable_backend_cannot_override_semantic_review(self):
        cases = (
            ('holder_count', -1, 'count', None), ('holder_count', True, 'count', None),
            ('price', -10, 'USD', None),
            ('price', 1, 'unknown', None), ('buys', 100, 'count', None),
            ('volume_24h', 100, 'USD', 1), ('creator', 'not-an-address', 'Address', None),
            ('created_timestamp', 0, 'UTC', None), ('is_honeypot', False, 'USD', None),
            ('buy_tax', 101, 'percent', None),
        )
        for key, value, unit, window in cases:
            with self.subTest(key=key, value=value, unit=unit):
                item = observation()
                item['fields'][key] = point(value, unit, window)
                original = deepcopy(item)
                result = process(item, self.ledger, Backend(), now=NOW)
                self.assertEqual(result['disposition'], 'review')
                self.assertTrue(result['reasons'])
                self.assertFalse(result['execution_authorized'])
                self.assertEqual(item, original)

    def test_invalid_shape_still_raises(self):
        item = observation()
        item['fields']['buys'] = point(1, 'count', True)
        with self.assertRaises(ValueError):
            normalize(item)
        item['fields']['buys'] = point({'nested': 1}, 'count', 60)
        with self.assertRaises(ValueError):
            normalize(item)

    def test_freshness_is_rechecked_after_inference(self):
        with patch('omnia_trading.pipeline._utcnow', side_effect=[NOW + timedelta(seconds=119), NOW + timedelta(seconds=121)]):
            result = process(observation(), self.ledger, Backend())
        self.assertEqual(result['disposition'], 'review')
        self.assertIn('stale_or_future:observation', result['reasons'])
        self.assertEqual(result['valid_until'], (NOW + timedelta(seconds=120)).isoformat())
        self.assertEqual(result['clock_mode'], 'realtime')

    def test_replay_time_is_explicit_and_model_cache_is_reused(self):
        item, backend = observation(), Backend()
        first = process(item, self.ledger, backend, now=NOW)
        second = process(item, self.ledger, backend, now=NOW + timedelta(minutes=10))
        self.assertEqual((first['disposition'], second['disposition']), ('candidate', 'review'))
        self.assertEqual(backend.calls, 2)
        self.assertNotEqual(first['assessment_id'], second['assessment_id'])
        self.assertNotEqual(first['evaluated_at'], second['evaluated_at'])
        self.assertEqual(second['clock_mode'], 'replay')
        self.assertTrue(all(record['cache_hit'] for record in second['groups'].values()))

    def test_all_dispositions_are_durable_with_policy_and_source(self):
        for disposition in ('candidate', 'review', 'skip'):
            item = observation()
            if disposition == 'review':
                item['fields']['holder_count'] = point(-1, 'count')
            elif disposition == 'skip':
                item['fields']['market_cap']['value'] = 1
            result = process(item, self.ledger, Backend(), now=NOW)
            self.assertEqual(result['disposition'], disposition)
            self.assertEqual(self.ledger.get_assessment(result['assessment_id']), result)
            self.assertEqual(result['source'], item['source'])
            self.assertTrue(result['evidence'])
            self.assertEqual(result['policy']['configuration']['max_age_seconds'], 120)
            self.assertFalse(result['execution_authorized'])

    def test_skip_preserves_uncertainty_and_all_rejection_reasons(self):
        item, backend = observation(), Backend()
        item['fields']['market_cap']['value'] = 1
        item['fields']['liquidity']['value'] = 1
        item['fields']['is_honeypot']['value'] = True
        result = process(item, self.ledger, backend, now=NOW + timedelta(hours=1))
        self.assertEqual(result['disposition'], 'skip')
        self.assertIn('stale_or_future:observation', result['reasons'])
        self.assertIn('below_policy_limit:market_cap', result['reasons'])
        self.assertIn('below_policy_limit:liquidity', result['reasons'])
        self.assertIn('source_reports_honeypot', result['reasons'])
        self.assertEqual(backend.calls, 0)

    def test_source_clock_and_event_time_consistency(self):
        item = observation()
        item['fields']['holder_count'] = point(1, 'count')
        item['fields']['holder_count']['observed_at'] = (NOW + timedelta(seconds=10)).isoformat()
        item['fields']['created_timestamp'] = point((NOW + timedelta(days=1)).timestamp(), 'unix_seconds')
        reasons = validate_semantics(normalize(item))
        self.assertIn('field_after_observation:holder_count', reasons)
        self.assertIn('future_event_time:created_timestamp', reasons)
        item['fields']['created_timestamp'] = point(NOW.timestamp() * 1000, 'unix_milliseconds')
        self.assertNotIn('future_event_time:created_timestamp', validate_semantics(normalize(item)))

    def test_comparable_cross_field_constraints_include_explicit_percent_conversion(self):
        item = observation()
        item['fields']['top_1_holder_rate'] = point(.5, 'ratio')
        item['fields']['top_10_holder_rate'] = point(10, 'percent')
        item['fields']['circulating_supply'] = point(200, 'tokens')
        item['fields']['total_supply'] = point(100, 'tokens')
        reasons = validate_semantics(normalize(item))
        self.assertIn('inconsistent_fields:top_1_holder_rate,top_10_holder_rate', reasons)
        self.assertIn('inconsistent_fields:circulating_supply,total_supply', reasons)
        self.assertNotIn('circulating_supply_fraction', derive_metrics(item, reasons))

    def test_metrics_require_aligned_window_clock_evidence_and_positive_denominator(self):
        item = observation()
        item['fields']['buys'] = point(3, 'count', 60)
        item['fields']['sells'] = point(1, 'count', 60)
        self.assertEqual(derive_metrics(item)['buy_share']['value'], .75)
        self.assertEqual(derive_metrics(item)['liquidity_to_market_cap']['value'], .4)
        for name, value in (('window_seconds', 300), ('observed_at', (NOW - timedelta(seconds=1)).isoformat()),
                            ('evidence', 'another:capture')):
            changed = deepcopy(item)
            changed['fields']['sells'][name] = value
            self.assertNotIn('buy_share', derive_metrics(changed))
        item['fields']['buys']['value'] = item['fields']['sells']['value'] = 0
        self.assertNotIn('buy_share', derive_metrics(item))

    def test_large_finite_counts_do_not_overflow_derived_ratios(self):
        item = observation()
        item['fields']['buys'] = point(10 ** 308, 'count', 60)
        item['fields']['sells'] = point(10 ** 308, 'count', 60)
        self.assertEqual(derive_metrics(normalize(item))['buy_share']['value'], .5)

    def test_catalog_union_is_partitioned_without_losing_fields(self):
        class Capture(Backend):
            def __init__(self):
                super().__init__()
                self.states = []

            def __call__(self, state, questions):
                self.states.append(deepcopy(state))
                return super().__call__(state, questions)

        item, backend = full_catalog_observation(), Capture()
        result = process(item, self.ledger, backend, now=NOW)
        self.assertEqual(len(result['groups']), len(result['assessment_batches']))
        self.assertEqual(result['group_failures'], {})
        covered = [key for batch in result['assessment_batches'].values() for key in batch['fields']]
        self.assertEqual(len(covered), len(set(covered)))
        self.assertEqual(set(covered) | set(result['unavailable_fields']), set(item['fields']))
        self.assertFalse(set(covered) & set(result['unavailable_fields']))
        self.assertEqual(result['parameter_count'], 102)
        for state in backend.states:
            self.assertLessEqual(len(state['fields']), 4)
            self.assertEqual(state['context']['identity'], item['identity'])
            self.assertEqual(state['context']['source'], item['source'])
            self.assertEqual(state['context']['observed_at'], item['observed_at'])

    def test_one_failed_batch_does_not_hide_other_fields(self):
        class FailPrice(Backend):
            def __call__(self, state, questions):
                if 'price' in state['fields']:
                    raise ValueError('controlled context-budget refusal')
                return super().__call__(state, questions)

        item = full_catalog_observation()
        result = process(item, self.ledger, FailPrice(), now=NOW)
        self.assertEqual(result['disposition'], 'review')
        self.assertEqual(len(result['group_failures']), 1)
        self.assertEqual(len(result['groups']) + len(result['group_failures']), len(result['assessment_batches']))
        name = next(iter(result['group_failures']))
        self.assertIn('price', result['assessment_batches'][name]['fields'])
        self.assertEqual(self.ledger.get_assessment(result['assessment_id']), result)

    def test_manifest_failure_is_a_durable_review(self):
        class Unavailable(Backend):
            def manifest(self):
                raise RuntimeError('private provider text')

        result = process(observation(), self.ledger, Unavailable(), now=NOW)
        self.assertEqual(result['disposition'], 'review')
        self.assertEqual(result['group_failures'], {'Market': 'RuntimeError', 'Risk': 'RuntimeError'})
        self.assertNotIn('private provider text', str(result))
        self.assertEqual(self.ledger.get_assessment(result['assessment_id']), result)

    def test_config_validates_and_freezes_policy_at_startup(self):
        with patch.dict(os.environ, {'OMNIA_LAYA_REVISION': 'a' * 40,
                                     'OMNIA_TRADING_MIN_MARKET_CAP_USD': '42000'}, clear=True):
            config = Config.from_env()
            os.environ['OMNIA_TRADING_MIN_MARKET_CAP_USD'] = '10'
            self.assertEqual(config.policy().min_market_cap_usd, 42000)
            os.environ['OMNIA_TRADING_MAX_AGE_SECONDS'] = 'nan'
            with self.assertRaises(ValueError):
                Config.from_env()
