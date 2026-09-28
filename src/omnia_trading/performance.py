# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Observed quote performance and an explicitly conditional position replay."""
from decimal import Decimal, localcontext
import math

from .contracts import timestamp
from .strategy_contracts import StrategyPolicy


def summarize_quotes(points, *, policy=None):
    """Replay independent entry at first quote, with no claim of fills or model decisions.

    Callers partition chain, network, token, pool and source before this function.
    Prices must share a verified unit. Exit fills use the next observed price,
    not an unobserved target price. Fees and slippage are excluded.
    """
    policy = policy or StrategyPolicy()
    ordered = sorted(points, key=lambda row: timestamp(row['at']))
    seen = set()
    for row in ordered:
        if type(row['price']) not in (int, float) or not math.isfinite(row['price']) or row['price'] <= 0:
            raise ValueError('invalid_quote_price')
        if not isinstance(row.get('evidence'), str) or not row['evidence'].strip():
            raise ValueError('quote_evidence_required')
        clock = timestamp(row['at'])
        if clock in seen:
            raise ValueError('duplicate_quote_clock')
        seen.add(clock)
    if len(ordered) < 2:
        return {'status': 'insufficient_quotes', 'quote_count': len(ordered), 'market': None, 'scenario': None}
    with localcontext() as context:
        context.prec = 50
        initial = Decimal(str(ordered[0]['price']))
        budget = Decimal(str(policy.entry_budget_usd))
        quantity = budget / initial
        initial_quantity = quantity
        cash, realized, high, drawdown = Decimal(0), Decimal(0), initial, Decimal(0)
        peak = initial
        milestones = {str(m): None for m in (2, 3, 5, 10)}
        events = [{'at': ordered[0]['at'], 'action': 'BUY', 'price': float(initial),
                   'quantity': float(quantity), 'evidence': ordered[0]['evidence'], 'reason': 'conditional_first_quote_entry'}]
        profit_taken = False
        gaps = []
        for previous, row in zip(ordered, ordered[1:]):
            price = Decimal(str(row['price']))
            peak, high = max(peak, price), max(high, price)
            drawdown = max(drawdown, 1 - price / high)
            gaps.append((timestamp(row['at']) - timestamp(previous['at'])).total_seconds())
            for multiple in milestones:
                if milestones[multiple] is None and price >= initial * Decimal(multiple):
                    milestones[multiple] = {'at': row['at'], 'price': float(price), 'evidence': row['evidence']}
            if not quantity:
                continue
            pnl = price / initial - 1
            sell = Decimal(0)
            if pnl <= -Decimal(str(policy.stop_loss_ratio)):
                action, sell = 'SL', quantity
            elif pnl >= Decimal(str(policy.take_profit_ratio)):
                action, sell = 'TP', quantity
            elif not profit_taken and pnl >= Decimal(str(policy.profit_trigger_ratio)):
                action = 'PROFIT'
                sell = quantity - initial_quantity * Decimal(str(policy.bag_fraction))
                profit_taken = True
            else:
                action = 'HOLD_BAG' if profit_taken else 'HOLD'
            cash += sell * price
            realized += sell * (price - initial)
            quantity -= sell
            events.append({'at': row['at'], 'action': action, 'price': float(price), 'sold_quantity': float(sell),
                           'remaining_quantity': float(quantity), 'realized_profit_usd': float(realized),
                           'evidence': row['evidence'], 'reason': 'conditional_exit_policy'})
        last = Decimal(str(ordered[-1]['price']))
        unrealized = quantity * (last - initial)
        result = {'status': 'observed', 'quote_count': len(ordered),
                  'first_at': ordered[0]['at'], 'last_at': ordered[-1]['at'], 'max_gap_seconds': max(gaps),
                  'market': {'first_price_usd': float(initial), 'last_price_usd': float(last),
                             'peak_price_usd': float(peak), 'peak_multiple': float(peak / initial),
                             'final_multiple': float(last / initial), 'return_ratio': float(last / initial - 1),
                             'max_drawdown_ratio': float(drawdown), 'milestones': milestones,
                             'hold_100_usd_profit': float(budget * (last / initial - 1)),
                             'reference_notional_usd': float(budget)},
                  'scenario': {'mode': 'conditional_first_quote_entry', 'entry_budget_usd': float(budget),
                               'fees_slippage_included': False, 'model_decision': False, 'orders_executed': False,
                               'realized_profit_usd': float(realized), 'unrealized_profit_usd': float(unrealized),
                               'gross_profit_usd': float(realized + unrealized),
                               'final_equity_usd': float(cash + quantity * last),
                               'open_quantity': float(quantity), 'final_action': events[-1]['action'], 'events': events}}
    def finite(value):
        if isinstance(value, dict):
            return all(finite(v) for v in value.values())
        if isinstance(value, list):
            return all(finite(v) for v in value)
        return not isinstance(value, float) or math.isfinite(value)
    if not finite(result):
        raise ValueError('performance_arithmetic_overflow')
    return result
