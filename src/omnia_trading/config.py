# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Configuration contains only consumed runtime and product settings."""
from dataclasses import dataclass, replace
import os
from ._engine.runtime import Settings
from .policy import Policy


@dataclass(frozen=True)
class Config:
    runtime: Settings
    max_records: int = 1000

    def __post_init__(self):
        if type(self.max_records) is not int or not 1 <= self.max_records <= 100000:
            raise ValueError('invalid_record_limit')

    @classmethod
    def from_env(cls):
        settings = replace(Settings.from_env(), database=os.environ.get('OMNIA_TRADING_DATABASE', 'var/trading/decisions.sqlite3'))
        return cls(settings, int(os.environ.get('OMNIA_TRADING_MAX_RECORDS', '1000')))

    def policy(self):
        return Policy(max_age_seconds=float(os.environ.get('OMNIA_TRADING_MAX_AGE_SECONDS', '120')),
                      min_market_cap_usd=float(os.environ.get('OMNIA_TRADING_MIN_MARKET_CAP_USD', '30000')),
                      min_liquidity_usd=float(os.environ.get('OMNIA_TRADING_MIN_LIQUIDITY_USD', '10000')))
