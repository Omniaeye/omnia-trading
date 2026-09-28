# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Configuration contains only consumed runtime and product settings."""
from dataclasses import dataclass, replace
import os
from ._engine.runtime import Settings
from .policy import Policy


def _env_bool(name, default=False):
    value = os.environ.get(name, str(default)).strip().lower()
    if value not in {'true', 'false', '1', '0'}:
        raise ValueError('invalid_boolean_environment:' + name)
    return value in {'true', '1'}


@dataclass(frozen=True)
class Config:
    runtime: Settings
    max_records: int = 1000
    trading_policy: Policy | None = None

    def __post_init__(self):
        if type(self.max_records) is not int or not 1 <= self.max_records <= 100000:
            raise ValueError('invalid_record_limit')
        if self.trading_policy is not None and not isinstance(self.trading_policy, Policy):
            raise ValueError('invalid_trading_policy')

    @classmethod
    def from_env(cls):
        settings = replace(Settings.from_env(), database=os.environ.get('OMNIA_TRADING_DATABASE', 'var/trading/decisions.sqlite3'))
        policy = Policy(max_age_seconds=float(os.environ.get('OMNIA_TRADING_MAX_AGE_SECONDS', '120')),
                        min_market_cap_usd=float(os.environ.get('OMNIA_TRADING_MIN_MARKET_CAP_USD', '30000')),
                        min_liquidity_usd=float(os.environ.get('OMNIA_TRADING_MIN_LIQUIDITY_USD', '10000')),
                        require_market_cap=_env_bool('OMNIA_TRADING_REQUIRE_MARKET_CAP'),
                        require_liquidity=_env_bool('OMNIA_TRADING_REQUIRE_LIQUIDITY'),
                        require_honeypot_report=_env_bool('OMNIA_TRADING_REQUIRE_HONEYPOT_REPORT'))
        return cls(settings, int(os.environ.get('OMNIA_TRADING_MAX_RECORDS', '1000')), policy)

    def policy(self):
        return self.trading_policy if self.trading_policy is not None else Policy()
