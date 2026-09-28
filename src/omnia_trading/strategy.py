# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Evidence assessment followed by deterministic position decisions."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import math
from decimal import Decimal, localcontext

from ._engine.ledger import digest, probability
from .contracts import normalize, timestamp
from .pipeline import process
from .policy import Policy, evaluate
from .strategy_contracts import STRATEGY_VERSION, StrategyPolicy, normalize_context
from .strategy_questions import STRATEGY_TASKS
from .validation import normalized_number
from .availability import reported_observation


def _now(now):
    return datetime.now(timezone.utc) if now is None else now


def _guards(item, context, policy, now):
    issues = []
    if context['identity'] != item['identity']:
        issues.append('position_identity_mismatch')
    age = (now - timestamp(context['observed_at'])).total_seconds()
    if age < -5 or age > policy.max_age_seconds:
        issues.append('stale_or_future:position')
    price = item['fields'].get('price')
    if not price or price['unit'] != 'USD' or type(price['value']) not in (int, float) or price['value'] <= 0:
        issues.append('missing_positive_usd_price')
    elif context['position']:
        marked_value = price['value'] * context['position']['quantity']
        if not math.isfinite(marked_value):
            issues.append('position_arithmetic_overflow')
        elif context['portfolio_exposure_usd'] + max(1e-8, marked_value * 1e-9) < marked_value:
            issues.append('portfolio_exposure_excludes_position')
    return issues


def _risk_reasons(fields, policy):
    reasons = []
    for key, rejected in (('is_honeypot', True), ('transfer_paused', True),
                          ('sell_simulation_success', False), ('is_wash_trading', True)):
        field = fields.get(key)
        if not field or field['value'] is None:
            if policy.require_risk_reports:
                reasons.append('missing_strategy_field:' + key)
        elif type(field['value']) is not bool:
            reasons.append('invalid_strategy_field:' + key)
        elif field['value'] is rejected:
            reasons.append('risk_rejected:' + key)
    for key in ('buy_tax', 'sell_tax'):
        field = fields.get(key)
        if field and field['value'] is not None and normalized_number(field) > policy.max_tax_ratio:
            reasons.append('tax_limit:' + key)
    return reasons


def _entry_reasons(item, assessment, context, policy):
    fields = reported_observation(item)[0]['fields']
    reasons = _risk_reasons(fields, policy)
    ownership = fields.get('top_10_holder_rate')
    if not ownership:
        if policy.require_ownership:
            reasons.append('missing_strategy_field:top_10_holder_rate')
    elif normalized_number(ownership) > policy.max_top_10_holder_ratio:
        reasons.append('holder_concentration_limit')
    metric = assessment['deterministic_metrics'].get('buy_share')
    if not metric or metric['window_seconds'] != policy.flow_window_seconds:
        reasons.append('missing_aligned_entry_flow')
    elif metric['value'] < policy.min_buy_share:
        reasons.append('buy_share_below_entry_limit')
    available = min(context['cash_available_usd'],
                    policy.max_portfolio_exposure_usd - context['portfolio_exposure_usd'])
    if available < policy.entry_budget_usd:
        reasons.append('insufficient_entry_budget')
    return reasons


def _task_coverage(item, context):
    fields = reported_observation(item)[0]['fields']
    coverage = {}
    for task, spec in STRATEGY_TASKS.items():
        supplied = [key for key in spec['fields'] if key in fields]
        missing = [key for key in spec['fields'] if key not in fields]
        needed = task == 'risk' or context['position'] is None
        coverage[task] = {
            'status': 'not_required_for_position' if not needed else
                      'complete' if not missing else 'partial' if supplied else 'not_reported',
            'reported_fields': supplied, 'missing_fields': missing,
            'inference_eligible': needed and not missing,
        }
    return coverage


def _model_checks(item, ledger, backend, policy, context, floor, max_bytes):
    records, failures = {}, {}
    try:
        manifest = {**backend.manifest(), 'task': STRATEGY_VERSION, 'policy': asdict(policy),
                    'observation_hash': digest(item), 'context_hash': digest(context)}
    except Exception as error:
        return {}, {'manifest': type(error).__name__}
    for task, spec in STRATEGY_TASKS.items():
        if not _task_coverage(item, context)[task]['inference_eligible']:
            continue
        fields = {key: item['fields'][key] for key in spec['fields'] if key in item['fields']}
        state = {'chain': item['identity']['chain'], 'task': task,
                 'fields': {key: {'value': value['value'], 'unit': value['unit'],
                                  'window_seconds': value['window_seconds']} for key, value in fields.items()}}
        if task == 'ownership':
            state['max_top_10_holder_ratio'] = policy.max_top_10_holder_ratio
        request = {'id': 'strategy:' + digest({'id': item['id'], 'task': task}),
                   'state': state, 'questions': {task: spec['question']},
                   'evidence': list(dict.fromkeys(f['evidence'] for f in fields.values()))}
        try:
            records[task] = ledger.decide(request, backend, manifest=manifest,
                                          min_probability=floor, max_bytes=max_bytes)
        except Exception as error:
            failures[task] = type(error).__name__
    return records, failures


def _price_exit_reached(item, context, policy):
    """Avoid additional inference when a validated position already meets an exit."""
    position = context['position']
    if position is None:
        return False
    with localcontext() as decimal_context:
        decimal_context.prec = 50
        pnl = Decimal(str(item['fields']['price']['value'])) / Decimal(str(position['average_entry_price_usd'])) - 1
    return pnl <= -Decimal(str(policy.stop_loss_ratio)) or pnl >= Decimal(str(policy.take_profit_ratio))


def _action(item, assessment, context, policy, checks, failures):
    position = context['position']
    if assessment['disposition'] != 'candidate':
        return 'SKIP', ['data_assessment:' + assessment['disposition']], {}
    price = item['fields']['price']['value']
    if position:
        with localcontext() as decimal_context:
            decimal_context.prec = 50
            pnl = float(Decimal(str(price)) / Decimal(str(position['average_entry_price_usd'])) - 1)
        quantity = position['quantity']
        value = price * quantity
        if not math.isfinite(pnl) or not math.isfinite(value):
            return 'SKIP', ['position_arithmetic_overflow'], {}
        state = {'unrealized_return_ratio': pnl, 'position_value_usd': value,
                 'realized_pnl_usd': position['realized_pnl_usd']}
        # Price protection takes precedence over partial exits and narrative/model views.
        if pnl <= -policy.stop_loss_ratio:
            return 'SL', ['stop_loss_reached'], {**state, 'reduce_quantity': quantity}
        if pnl >= policy.take_profit_ratio:
            return 'TP', ['take_profit_reached'], {**state, 'reduce_quantity': quantity}
        if value > policy.max_position_usd or context['portfolio_exposure_usd'] > policy.max_portfolio_exposure_usd:
            return 'SKIP', ['exposure_limit_requires_rebalance'], state
        risk_reasons = _risk_reasons(reported_observation(item)[0]['fields'], policy)
        if risk_reasons:
            return 'SKIP', risk_reasons, state
        required = {task for task, c in _task_coverage(item, context).items() if c['inference_eligible']}
        if failures or any(r['status'] != 'accepted' for r in checks.values()) or set(checks) != required:
            return 'SKIP', ['strategy_evidence_requires_review'], state
        if 'risk' in checks and checks['risk']['answers']['risk']['choice'] != 'clear':
            return 'SKIP', ['risk_requires_review'], state
        bag = position['initial_quantity'] * policy.bag_fraction
        if pnl >= policy.profit_trigger_ratio and not position['profit_taken'] and quantity > bag:
            return 'PROFIT', ['partial_profit_reached'], {**state, 'reduce_quantity': quantity - bag,
                                                        'retain_quantity': bag}
        if position['profit_taken'] and quantity <= bag:
            return 'HOLD_BAG', ['residual_position_within_policy'], state
        return 'HOLD', ['position_within_exit_limits'], state
    reasons = _entry_reasons(item, assessment, context, policy)
    required = {task for task, c in _task_coverage(item, context).items() if c['inference_eligible']}
    if failures or set(checks) != required:
        reasons.append('strategy_processing_incomplete')
    for task, record in checks.items():
        if record['status'] != 'accepted' or record['answers'][task]['choice'] != STRATEGY_TASKS[task]['accepted']:
            reasons.append('strategy_rejected:' + task)
    if reasons:
        return 'SKIP', reasons, {}
    return 'BUY', ['entry_policy_satisfied'], {'entry_notional_usd': policy.entry_budget_usd}


def decide(event, context, ledger, backend, *, strategy_policy=None, data_policy=None,
           min_probability=.8, max_bytes=65536, now=None):
    """Produce a persisted strategy decision; no order is signed or submitted."""
    item = normalize(event, max_bytes)
    context = normalize_context(context)
    strategy_policy = strategy_policy or StrategyPolicy()
    data_policy = data_policy or Policy()
    floor = probability(min_probability)
    started = _now(now)
    assessment = process(item, ledger, backend, policy=data_policy, now=now,
                         min_probability=floor, max_bytes=max_bytes)
    issues = _guards(item, context, data_policy, started)
    checks, failures = {}, {}
    price_exit = False
    if assessment['disposition'] == 'candidate' and not issues:
        if not context['position']:
            issues.extend(_entry_reasons(item, assessment, context, strategy_policy))
        price_exit = _price_exit_reached(item, context, strategy_policy)
        # The data assessment remains required; strategy inference must not delay a price exit.
        if not issues and not price_exit:
            checks, failures = _model_checks(item, ledger, backend, strategy_policy, context, floor, max_bytes)
    evaluated = _now(now)
    issues.extend(_guards(item, context, data_policy, evaluated))
    disposition, freshness = evaluate(item, data_policy, evaluated)
    if disposition != 'observe':
        issues.extend(freshness or ['data_policy:' + disposition])
    if issues:
        action, reasons, sizing = 'SKIP', list(dict.fromkeys(issues)), {}
    else:
        action, reasons, sizing = _action(item, assessment, context, strategy_policy, checks, failures)
    try:
        context_expiry = timestamp(context['observed_at']) + timedelta(seconds=data_policy.max_age_seconds)
    except OverflowError:
        context_expiry = datetime.max.replace(tzinfo=timezone.utc)
    expiry = min(timestamp(assessment['valid_until']), context_expiry)
    result = {
        'schema': STRATEGY_VERSION, 'action': action, 'reasons': reasons, 'sizing': sizing,
        'identity': item['identity'], 'observation_id': item['id'], 'observation_hash': digest(item),
        'data_assessment_id': assessment['assessment_id'], 'data_disposition': assessment['disposition'],
        'context_hash': digest(context), 'position_id': context['position']['id'] if context['position'] else None,
        'evidence': list(dict.fromkeys([*assessment['evidence'], context['evidence']])),
        'strategy_policy': asdict(strategy_policy), 'min_answer_probability': floor,
        'strategy_checks': checks, 'strategy_failures': failures,
        'strategy_check_mode': 'price_exit' if price_exit else 'coverage_gated',
        'strategy_coverage': _task_coverage(item, context),
        'evaluated_at': evaluated.isoformat(), 'valid_until': expiry.isoformat(),
        'clock_mode': 'realtime' if now is None else 'replay', 'execution_authorized': False,
    }
    result['decision_key'] = digest({'observation': digest(item), 'context': digest(context),
                                     'policy': asdict(strategy_policy), 'data_policy': asdict(data_policy),
                                     'action': action, 'sizing': sizing, 'version': STRATEGY_VERSION})
    return ledger.record_assessment(result)


def process_strategy(envelope, ledger, backend, **kwargs):
    """JSONL strategy envelope keeps position snapshots bound to each observation."""
    if not isinstance(envelope, dict) or set(envelope) != {'observation', 'context', 'strategy_policy'}:
        raise ValueError('invalid_strategy_envelope')
    if not isinstance(envelope['strategy_policy'], dict):
        raise ValueError('invalid_strategy_policy')
    return decide(envelope['observation'], envelope['context'], ledger, backend,
                  strategy_policy=StrategyPolicy(**envelope['strategy_policy']), **kwargs)
