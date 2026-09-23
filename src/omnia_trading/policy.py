# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Deterministic completeness and market-policy checks precede model assessment."""
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from .contracts import timestamp


@dataclass(frozen=True)
class Policy:
    max_age_seconds: int = 120
    min_market_cap_usd: float = 30000
    min_liquidity_usd: float = 10000

    def __post_init__(self):
        for value in (self.max_age_seconds, self.min_market_cap_usd, self.min_liquidity_usd):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('invalid_policy_limit')


def evaluate(event, policy, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('timezone_required')
    fields = event['fields']
    issues = []
    envelope_age = (now - timestamp(event['observed_at'])).total_seconds()
    if envelope_age < -5 or envelope_age > policy.max_age_seconds:
        issues.append('stale_or_future:observation')
    for key, field in fields.items():
        age = (now - timestamp(field['observed_at'])).total_seconds()
        if age < -5 or age > policy.max_age_seconds:
            issues.append('stale_or_future:' + key)
    for key, minimum in (('market_cap', policy.min_market_cap_usd), ('liquidity', policy.min_liquidity_usd)):
        field = fields.get(key)
        if not field or field['unit'] != 'USD' or type(field['value']) not in (int, float):
            issues.append('missing_usd_value:' + key)
        elif field['value'] < minimum:
            return 'skip', ['below_policy_limit:' + key]
    risk = fields.get('is_honeypot')
    if not risk or type(risk['value']) is not bool:
        issues.append('missing_risk_flag:is_honeypot')
    elif risk['value']:
        return 'skip', ['source_reports_honeypot']
    return ('review', issues) if issues else ('observe', [])
