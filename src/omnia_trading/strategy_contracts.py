# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Position snapshots and explicit strategy limits, independent of source fields."""
from dataclasses import asdict, dataclass
import math
from .contracts import timestamp
from .identity import identity

STRATEGY_VERSION = 'omnia.trading.strategy.v1'
ACTIONS = ('SKIP', 'BUY', 'HOLD', 'HOLD_BAG', 'PROFIT', 'TP', 'SL')


def _number(value, name, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError('invalid_strategy_number:' + name)


@dataclass(frozen=True)
class StrategyPolicy:
    entry_budget_usd: float = 100
    max_position_usd: float = 500
    max_portfolio_exposure_usd: float = 5000
    min_buy_share: float = .60
    flow_window_seconds: int = 300
    max_top_10_holder_ratio: float = .50
    max_tax_ratio: float = .05
    stop_loss_ratio: float = .10
    profit_trigger_ratio: float = .25
    take_profit_ratio: float = .50
    bag_fraction: float = .20

    def __post_init__(self):
        for name, value in asdict(self).items():
            _number(value, name, positive=name not in {'max_tax_ratio'})
        for name in ('min_buy_share', 'max_top_10_holder_ratio', 'max_tax_ratio'):
            if getattr(self, name) > 1:
                raise ValueError('invalid_strategy_ratio:' + name)
        if not 0 < self.stop_loss_ratio < 1 or not 0 < self.bag_fraction < 1:
            raise ValueError('invalid_position_ratio')
        if self.take_profit_ratio <= self.profit_trigger_ratio:
            raise ValueError('take_profit_must_exceed_partial_profit')
        if not self.entry_budget_usd <= self.max_position_usd <= self.max_portfolio_exposure_usd:
            raise ValueError('inconsistent_exposure_limits')
        if type(self.flow_window_seconds) is not int or self.flow_window_seconds > 2592000:
            raise ValueError('invalid_flow_window')


def normalize_context(context):
    if not isinstance(context, dict) or set(context) != {
        'identity', 'observed_at', 'evidence', 'cash_available_usd', 'portfolio_exposure_usd', 'position'
    }:
        raise ValueError('invalid_strategy_context')
    result = {**context, 'identity': identity(context['identity'])}
    timestamp(result['observed_at'])
    if not isinstance(result['evidence'], str) or not result['evidence'].strip() or len(result['evidence']) > 512:
        raise ValueError('invalid_position_evidence')
    for name in ('cash_available_usd', 'portfolio_exposure_usd'):
        _number(result[name], name)
    position = context['position']
    if position is not None:
        if not isinstance(position, dict) or set(position) != {
            'id', 'quantity', 'initial_quantity', 'average_entry_price_usd', 'profit_taken', 'realized_pnl_usd'
        }:
            raise ValueError('invalid_position')
        if not isinstance(position['id'], str) or not position['id'].strip() or len(position['id']) > 200:
            raise ValueError('invalid_position_id')
        for name in ('quantity', 'initial_quantity', 'average_entry_price_usd'):
            _number(position[name], name, positive=True)
        pnl = position['realized_pnl_usd']
        if type(pnl) not in (int, float) or not math.isfinite(pnl):
            raise ValueError('invalid_realized_pnl')
        if type(position['profit_taken']) is not bool or position['quantity'] > position['initial_quantity']:
            raise ValueError('invalid_position_state')
        result['position'] = dict(position)
    return result
