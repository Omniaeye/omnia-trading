# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Deterministic completeness and market-policy checks precede model assessment."""
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from .contracts import timestamp
from .validation import field_issues, validate_semantics

POLICY_VERSION = 'omnia.trading.data-policy.v2'


@dataclass(frozen=True)
class Policy:
    max_age_seconds: float = 120
    min_market_cap_usd: float = 30000
    min_liquidity_usd: float = 10000

    def __post_init__(self):
        for value in (self.max_age_seconds, self.min_market_cap_usd, self.min_liquidity_usd):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('invalid_policy_limit')


def evaluate(event, policy, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('timezone_required')
    fields = event['fields']
    issues = validate_semantics(event)
    rejection_reasons = []
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
        elif not field_issues(key, field, event['identity']['chain']) and field['value'] < minimum:
            rejection_reasons.append('below_policy_limit:' + key)
    risk = fields.get('is_honeypot')
    if not risk or type(risk['value']) is not bool:
        issues.append('missing_risk_flag:is_honeypot')
    elif not field_issues('is_honeypot', risk, event['identity']['chain']) and risk['value']:
        rejection_reasons.append('source_reports_honeypot')
    # A well-formed rejecting value wins conservatively, but no uncertainty is discarded.
    reasons = list(dict.fromkeys([*issues, *rejection_reasons]))
    if rejection_reasons:
        return 'skip', reasons
    return ('review', reasons) if reasons else ('observe', [])
