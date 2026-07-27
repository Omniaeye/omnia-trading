# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Descriptive arithmetic over aligned source aggregates, never trade inference."""
import math
from decimal import Decimal, localcontext

from .validation import comparable, field_issues


def derive_metrics(event, issues=()):
    fields, chain = event['fields'], event['identity']['chain']
    metrics = {}

    def number(key):
        return Decimal(str(fields[key]['value']))

    def calculate(operation):
        with localcontext() as context:
            context.prec = 50
            return float(operation())

    def ready(keys, window=False):
        if not comparable(fields, keys, require_window=window):
            return False
        if any(field_issues(key, fields[key], chain) for key in keys):
            return False
        return not any(any(key in issue.split(':', 1)[-1].split(',') for key in keys) for issue in issues)

    def add(name, keys, value, unit, formula):
        if not math.isfinite(value):
            return
        first = fields[keys[0]]
        metrics[name] = {'value': value, 'unit': unit, 'inputs': list(keys), 'formula': formula,
                         'window_seconds': first['window_seconds'], 'observed_at': first['observed_at'],
                         'evidence': [first['evidence']]}

    keys = ('buys', 'sells')
    if ready(keys, True):
        if fields['buys']['value'] > 0 or fields['sells']['value'] > 0:
            add('buy_share', keys, calculate(lambda: number('buys') / (number('buys') + number('sells'))),
                'ratio', 'buys / (buys + sells)')
    keys = ('buy_volume', 'sell_volume')
    if ready(keys, True):
        add('net_buy_volume', keys, calculate(lambda: number('buy_volume') - number('sell_volume')),
            fields['buy_volume']['unit'], 'buy_volume - sell_volume')
    for name, numerator, denominator in (
        ('liquidity_to_market_cap', 'liquidity', 'market_cap'),
        ('circulating_supply_fraction', 'circulating_supply', 'total_supply'),
    ):
        keys = (numerator, denominator)
        if ready(keys) and fields[denominator]['value'] > 0:
            value = calculate(lambda: number(numerator) / number(denominator))
            if name != 'circulating_supply_fraction' or value <= 1:
                add(name, keys, value, 'ratio', numerator + ' / ' + denominator)
    return metrics
