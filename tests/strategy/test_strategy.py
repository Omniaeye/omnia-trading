# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Strategy lifecycle regressions with a controlled typed-answer backend."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from omnia_trading._engine.ledger import DecisionLedger
from omnia_trading.strategy import process_strategy
from omnia_trading.strategy_contracts import StrategyPolicy

ROOT = Path(__file__).resolve().parents[2]


class TypedBackend:
    def __init__(self, overrides=None, fail_strategy=False):
        self.overrides = overrides or {}
        self.fail_strategy = fail_strategy
        self.calls = 0

    def manifest(self):
        return {'controlled_strategy_backend': 1, 'overrides': self.overrides, 'fail_strategy': self.fail_strategy}

    def __call__(self, state, questions):
        self.calls += 1
        answers = {}
        for name, question in questions.items():
            if self.fail_strategy and name != 'quality':
                raise RuntimeError('controlled strategy failure')
            labels = list(question['criteria'])
            chosen = self.overrides.get(name, labels[0])
            answers[name] = {'type': 'choice', 'choice': chosen,
                             'probabilities': {key: .9 if key == chosen else .1 / (len(labels) - 1) for key in labels}}
        return {'answers': answers}


class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.ledger = DecisionLedger(Path(self.folder.name) / 'strategy.db')
        self.envelope = json.loads((ROOT / 'examples/strategy.jsonl').read_text())
        self.now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
        self.backend = TypedBackend()

    def tearDown(self):
        self.ledger.close()
        self.folder.cleanup()

    def decide(self, **kwargs):
        return process_strategy(self.envelope, self.ledger, self.backend, now=self.now, **kwargs)

    def position(self, price=1.1, quantity=100, profit_taken=False):
        self.envelope['observation']['fields']['price']['value'] = price
        self.envelope['context']['position'] = {
            'id': 'position-1', 'quantity': quantity, 'initial_quantity': 100,
            'average_entry_price_usd': 1, 'profit_taken': profit_taken, 'realized_pnl_usd': 0,
        }
        self.envelope['context']['portfolio_exposure_usd'] = price * quantity

    def test_buy_requires_all_typed_tasks_and_keeps_execution_separate(self):
        result = self.decide()
        self.assertEqual(result['action'], 'BUY')
        self.assertEqual(result['sizing']['entry_notional_usd'], 100)
        self.assertEqual(set(result['strategy_checks']), {'risk', 'flow', 'ownership'})
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(self.ledger.get_assessment(result['assessment_id']), result)

    def test_all_seven_actions_are_reachable(self):
        cases = [('HOLD', 1.10, 100, False), ('PROFIT', 1.25, 100, False),
                 ('HOLD_BAG', 1.30, 20, True), ('TP', 1.50, 100, False), ('SL', .90, 100, False)]
        for action, price, quantity, taken in cases:
            with self.subTest(action=action):
                self.position(price, quantity, taken)
                self.assertEqual(self.decide()['action'], action)
        self.envelope['context']['position'] = None
        self.envelope['context']['cash_available_usd'] = 0
        self.assertEqual(self.decide()['action'], 'SKIP')

    def test_partial_profit_retains_fraction_of_initial_quantity(self):
        self.position(1.3)
        result = self.decide()
        self.assertEqual(result['sizing']['reduce_quantity'], 80)
        self.assertEqual(result['sizing']['retain_quantity'], 20)
        self.position(1.3, 20, True)
        self.assertEqual(self.decide()['action'], 'HOLD_BAG')

    def test_final_take_profit_precedes_partial_profit(self):
        self.position(1.5)
        self.assertEqual(self.decide()['action'], 'TP')

    def test_stop_loss_exact_decimal_boundary(self):
        self.position(.90)
        result = self.decide()
        self.assertEqual(result['action'], 'SL')
        self.assertEqual(result['sizing']['reduce_quantity'], 100)

    def test_strategy_outage_does_not_override_price_exit(self):
        self.backend = TypedBackend(fail_strategy=True)
        self.position(.8)
        self.assertEqual(self.decide()['action'], 'SL')
        self.position(1.1)
        self.assertEqual(self.decide()['action'], 'SKIP')

    def test_price_exit_never_calls_additional_strategy_inference(self):
        class NoStrategyBackend(TypedBackend):
            def __call__(self, state, questions):
                if set(questions) != {'quality'}:
                    self.strategy_calls.append(tuple(questions))
                return super().__call__(state, questions)

        self.backend = NoStrategyBackend()
        self.backend.strategy_calls = []
        for price, action in ((.8, 'SL'), (1.6, 'TP')):
            with self.subTest(action=action):
                self.position(price)
                result = self.decide()
                self.assertEqual(result['action'], action)
                self.assertEqual(result['strategy_checks'], {})
                self.assertEqual(result['strategy_check_mode'], 'price_exit')
                self.assertEqual(self.backend.strategy_calls, [])

    def test_risk_flags_override_confident_model_for_entry_and_hold(self):
        for held in (False, True):
            for key, value in [('transfer_paused', True), ('sell_simulation_success', False), ('is_wash_trading', True)]:
                with self.subTest(held=held, key=key):
                    original = deepcopy(self.envelope)
                    if held:
                        self.position()
                    self.envelope['observation']['fields'][key]['value'] = value
                    self.assertEqual(self.decide()['action'], 'SKIP')
                    self.envelope = original

    def test_expired_context_cannot_buy_or_exit(self):
        self.envelope['context']['observed_at'] = (self.now - timedelta(seconds=121)).isoformat()
        self.assertEqual(self.decide()['action'], 'SKIP')
        self.position(.8)
        self.assertEqual(self.decide()['action'], 'SKIP')

    def test_identity_mismatch_is_skipped(self):
        self.envelope['context']['identity']['contract'] = '0x' + '2' * 40
        self.assertEqual(self.decide()['action'], 'SKIP')

    def test_window_or_source_mismatch_prevents_entry(self):
        self.envelope['observation']['fields']['sells']['evidence'] = 'different:capture'
        self.assertEqual(self.decide()['action'], 'SKIP')

    def test_exposure_and_cash_limits(self):
        for key, value in [('cash_available_usd', 99), ('portfolio_exposure_usd', 4950)]:
            with self.subTest(key=key):
                original = deepcopy(self.envelope)
                self.envelope['context'][key] = value
                self.assertEqual(self.decide()['action'], 'SKIP')
                self.envelope = original

    def test_model_rejection_cannot_enter(self):
        self.backend = TypedBackend({'flow': 'weak'})
        self.assertEqual(self.decide()['action'], 'SKIP')

    def test_data_review_blocks_strategy(self):
        self.backend = TypedBackend({'quality': 'insufficient'})
        self.assertEqual(self.decide()['action'], 'SKIP')

    def test_repeated_request_reuses_model_records_and_decision_key(self):
        first = self.decide()
        calls = self.backend.calls
        second = self.decide()
        self.assertEqual(self.backend.calls, calls)
        self.assertEqual(first['decision_key'], second['decision_key'])
        self.assertTrue(all(row['cache_hit'] for row in second['strategy_checks'].values()))

    def test_position_change_changes_proposal_identity(self):
        self.position(1.3)
        first = self.decide()
        self.position(1.3, 20, True)
        second = self.decide()
        self.assertNotEqual(first['decision_key'], second['decision_key'])

    def test_invalid_policy_rejected(self):
        for options in ({'entry_budget_usd': True}, {'bag_fraction': 1}, {'take_profit_ratio': .2},
                        {'flow_window_seconds': 1.5}, {'max_tax_ratio': -1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                StrategyPolicy(**options)

    def test_closed_position_requires_null(self):
        self.position(quantity=0)
        with self.assertRaises(ValueError):
            self.decide()

    def test_portfolio_exposure_includes_held_position(self):
        self.position()
        self.envelope['context']['portfolio_exposure_usd'] = 0
        result = self.decide()
        self.assertEqual(result['action'], 'SKIP')
        self.assertIn('portfolio_exposure_excludes_position', result['reasons'])

    def test_missing_optional_reports_do_not_call_risk_or_ownership_model(self):
        fields = self.envelope['observation']['fields']
        for key in ('is_honeypot', 'transfer_paused', 'sell_simulation_success', 'is_wash_trading',
                    'top_10_holder_rate', 'market_cap', 'liquidity'):
            fields.pop(key)
        result = self.decide()
        self.assertEqual(result['action'], 'BUY')
        self.assertEqual(set(result['strategy_checks']), {'flow'})
        self.assertEqual(result['strategy_coverage']['risk']['status'], 'not_reported')
        self.assertEqual(result['strategy_coverage']['ownership']['status'], 'not_reported')
        self.assertFalse(result['execution_authorized'])

    def test_partial_risk_keeps_coverage_and_still_rejects_known_risk(self):
        del self.envelope['observation']['fields']['sell_simulation_success']
        result = self.decide()
        self.assertEqual(result['action'], 'BUY')
        self.assertEqual(result['strategy_coverage']['risk']['status'], 'partial')
        self.assertNotIn('risk', result['strategy_checks'])
        self.envelope['observation']['fields']['transfer_paused']['value'] = True
        result = self.decide()
        self.assertEqual(result['action'], 'SKIP')
        self.assertIn('risk_rejected:transfer_paused', result['reasons'])

    def test_operator_can_require_all_risk_reports(self):
        del self.envelope['observation']['fields']['is_wash_trading']
        self.envelope['strategy_policy']['require_risk_reports'] = True
        result = self.decide()
        self.assertEqual(result['action'], 'SKIP')
        self.assertIn('missing_strategy_field:is_wash_trading', result['reasons'])

    def test_operator_can_require_ownership(self):
        del self.envelope['observation']['fields']['top_10_holder_rate']
        self.envelope['strategy_policy']['require_ownership'] = True
        result = self.decide()
        self.assertEqual(result['action'], 'SKIP')
        self.assertIn('missing_strategy_field:top_10_holder_rate', result['reasons'])

    def test_missing_flow_or_price_still_blocks_entry(self):
        for key in ('buys', 'sells', 'price'):
            with self.subTest(key=key):
                original = deepcopy(self.envelope)
                del self.envelope['observation']['fields'][key]
                self.assertEqual(self.decide()['action'], 'SKIP')
                self.envelope = original

    def test_existing_position_does_not_require_entry_flow_or_ownership(self):
        self.position()
        for key in ('buys', 'sells', 'top_10_holder_rate'):
            del self.envelope['observation']['fields'][key]
        result = self.decide()
        self.assertEqual(result['action'], 'HOLD')
        self.assertEqual(set(result['strategy_checks']), {'risk'})
        self.assertEqual(result['strategy_coverage']['flow']['status'], 'not_required_for_position')

    def test_null_optional_field_is_not_given_to_model(self):
        self.envelope['observation']['fields']['top_10_holder_rate']['value'] = None
        result = self.decide()
        self.assertEqual(result['action'], 'BUY')
        self.assertNotIn('ownership', result['strategy_checks'])

    def test_invalid_optional_field_still_blocks(self):
        self.envelope['observation']['fields']['top_10_holder_rate']['unit'] = 'unknown_scale'
        self.assertEqual(self.decide()['action'], 'SKIP')

    def test_price_exit_with_no_optional_reports(self):
        self.position(.8)
        self.envelope['observation']['fields'] = {'price': self.envelope['observation']['fields']['price']}
        result = self.decide()
        self.assertEqual(result['action'], 'SL')
        self.assertEqual(result['sizing']['reduce_quantity'], 100)
        self.assertEqual(result['strategy_checks'], {})
