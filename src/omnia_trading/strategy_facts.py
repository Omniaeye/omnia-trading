# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Read-only strategy facts for shadow comparison with native model answers."""
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext

from ._engine.ledger import digest
from .contracts import normalize, timestamp
from .policy import Policy
from .strategy_contracts import StrategyPolicy
from .validation import comparable, field_issues, normalized_number, validate_semantics

FACTS_VERSION = 'omnia.trading.strategy-facts.v1'
RISK_FLAGS = {'is_honeypot': True, 'transfer_paused': True,
              'sell_simulation_success': False, 'is_wash_trading': True}


def assess_facts(event, *, policy=None, data_policy=None, now=None):
    """Preserve all fields; only aligned, fresh, validated values support a fact.

    This result is not a strategy action and is not wired into the order path.
    Confidence from a model cannot replace missing source evidence.
    """
    item = normalize(event)
    policy, data_policy = policy or StrategyPolicy(), data_policy or Policy()
    evaluated = datetime.now(timezone.utc) if now is None else now
    if not isinstance(evaluated, datetime) or evaluated.tzinfo is None or evaluated.utcoffset() is None:
        raise ValueError('timezone_required')
    fields, chain = item['fields'], item['identity']['chain']
    envelope_time = timestamp(item['observed_at'])
    envelope_age = (evaluated - envelope_time).total_seconds()
    semantic_issues = validate_semantics(item)
    eligible, quarantined = {}, {}
    for key, field in fields.items():
        issues = field_issues(key, field, chain)
        age = (evaluated - timestamp(field['observed_at'])).total_seconds()
        if envelope_age < -5 or envelope_age > data_policy.max_age_seconds:
            issues.append('stale_or_future:observation')
        if age < -5 or age > data_policy.max_age_seconds:
            issues.append('stale_or_future:' + key)
        for issue in semantic_issues:
            if key in issue.split(':', 1)[-1].split(','):
                issues.append(issue)
        if issues:
            quarantined[key] = {'field': field, 'reasons': list(dict.fromkeys(issues))}
        else:
            eligible[key] = field

    def record(choice, keys, reasons=(), **details):
        missing = ['missing_field:' + key for key in keys if key not in fields]
        invalid = [reason for key in keys if key in quarantined for reason in quarantined[key]['reasons']]
        return {'choice': choice, 'inputs': {key: fields[key] for key in keys if key in fields},
                'evidence': list(dict.fromkeys(fields[key]['evidence'] for key in keys if key in fields)),
                'reasons': list(dict.fromkeys([*reasons, *missing, *invalid])), **details}

    rejecting = [key for key, rejected in RISK_FLAGS.items()
                 if key in eligible and eligible[key]['value'] is rejected]
    risk = 'reject' if rejecting else 'clear' if all(key in eligible for key in RISK_FLAGS) else 'unknown'
    checks = {'risk': record(risk, RISK_FLAGS, ['source_reports_risk:' + key for key in rejecting])}

    flow_keys = ('buys', 'sells')
    flow, share, threshold_met = 'unknown', None, None
    reasons = []
    if all(key in eligible for key in flow_keys):
        if not comparable(eligible, flow_keys, require_window=True):
            reasons.append('unaligned_flow')
        elif eligible['buys']['window_seconds'] != policy.flow_window_seconds:
            reasons.append('unexpected_strategy_window')
        else:
            buys, sells = (eligible[key]['value'] for key in flow_keys)
            flow = 'supportive' if buys > sells else 'weak'
            with localcontext() as context:
                context.prec = 50
                total = Decimal(buys) + Decimal(sells)
                share = float(Decimal(buys) / total) if total else None
                threshold_met = bool(total and Decimal(buys) >= Decimal(str(policy.min_buy_share)) * total)
    checks['flow'] = record(flow, flow_keys, reasons, buy_share=share, entry_threshold_met=threshold_met,
                            min_buy_share=policy.min_buy_share, required_window_seconds=policy.flow_window_seconds)

    ownership = eligible.get('top_10_holder_rate')
    ratio = normalized_number(ownership) if ownership else None
    choice = 'unknown' if ratio is None else 'concentrated' if ratio > policy.max_top_10_holder_ratio else 'within_limit'
    checks['ownership'] = record(choice, ('top_10_holder_rate',), ratio=ratio,
                                 max_top_10_holder_ratio=policy.max_top_10_holder_ratio)
    return {'schema': FACTS_VERSION, 'engine': 'deterministic', 'observation_id': item['id'],
            'observation_hash': digest(item), 'identity': item['identity'], 'checks': checks,
            'eligible_fields': eligible, 'quarantined_fields': quarantined,
            'strategy_policy': asdict(policy), 'data_policy': asdict(data_policy),
            'evaluated_at': evaluated.isoformat(), 'clock_mode': 'realtime' if now is None else 'replay',
            'execution_authorized': False}
