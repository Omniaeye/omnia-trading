# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Replay accounting, observable milestones and chronological exit precedence."""
import unittest
from omnia_trading.performance import summarize_quotes


def quotes(prices):
    return [{'at': f'2026-09-28T12:00:{i:02}+00:00', 'price': price, 'evidence': f'capture:{i}'}
            for i, price in enumerate(prices)]


class PerformanceTests(unittest.TestCase):
    def test_peak_double_is_not_final_double(self):
        result = summarize_quotes(quotes([1, 2.1, 1.2]))
        self.assertIsNotNone(result['market']['milestones']['2'])
        self.assertAlmostEqual(result['market']['final_multiple'], 1.2)
        self.assertEqual(result['scenario']['final_action'], 'TP')
        self.assertAlmostEqual(result['scenario']['gross_profit_usd'], 110)

    def test_partial_profit_and_bag_accounting(self):
        result = summarize_quotes(quotes([1, 1.25, 1.3]))['scenario']
        self.assertEqual([e['action'] for e in result['events']], ['BUY', 'PROFIT', 'HOLD_BAG'])
        self.assertAlmostEqual(result['realized_profit_usd'], 20)
        self.assertAlmostEqual(result['unrealized_profit_usd'], 6)
        self.assertAlmostEqual(result['final_equity_usd'], 126)

    def test_stop_uses_observed_quote_not_target(self):
        result = summarize_quotes(quotes([1, .7, 2]))['scenario']
        self.assertEqual(result['final_action'], 'SL')
        self.assertAlmostEqual(result['gross_profit_usd'], -30)
        self.assertEqual(len(result['events']), 2)

    def test_partial_then_stop_accounts_for_both_exits(self):
        result = summarize_quotes(quotes([1, 1.25, .9]))['scenario']
        self.assertAlmostEqual(result['gross_profit_usd'], 18)
        self.assertEqual(result['open_quantity'], 0)

    def test_holding_has_unrealized_not_realized_profit(self):
        result = summarize_quotes(quotes([1, 1.1]))['scenario']
        self.assertEqual(result['realized_profit_usd'], 0)
        self.assertAlmostEqual(result['unrealized_profit_usd'], 10)
        self.assertFalse(result['orders_executed'])

    def test_single_quote_does_not_imply_zero_return(self):
        result = summarize_quotes(quotes([1]))
        self.assertEqual(result['status'], 'insufficient_quotes')
        self.assertIsNone(result['market'])

    def test_sorts_clocks_and_rejects_duplicate(self):
        self.assertAlmostEqual(summarize_quotes(list(reversed(quotes([1, 1.1]))))['market']['return_ratio'], .1)
        with self.assertRaisesRegex(ValueError, 'duplicate_quote_clock'):
            summarize_quotes(quotes([1]) * 2)

    def test_bad_price_is_not_a_loss(self):
        with self.assertRaisesRegex(ValueError, 'invalid_quote_price'):
            summarize_quotes(quotes([1, 0]))

    def test_unchanged_quotes_are_hold_not_missing(self):
        result = summarize_quotes(quotes([1, 1, 1]))
        self.assertEqual(result['scenario']['final_action'], 'HOLD')
        self.assertEqual(result['market']['return_ratio'], 0)


if __name__ == '__main__':
    unittest.main()
