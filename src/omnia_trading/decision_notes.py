# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Source-bound explanations; rules and native inference retain separate authorship."""
from ._engine.ledger import digest
from .strategy_facts import assess_facts
from .policy import Policy


def explain_observation(event, *, policy=None, data_policy=None, now=None, native_checks=None):
    facts = assess_facts(event, policy=policy, data_policy=data_policy, now=now)
    limits = facts['strategy_policy']
    data_policy = data_policy or Policy()
    valid = facts['eligible_fields']
    notes = []

    def add(code, task, level, text, keys=(), values=None, origin='rule'):
        notes.append({'code': code, 'task': task, 'level': level, 'text': text, 'origin': origin,
                      'values': values or {},
                      'evidence': list(dict.fromkeys(event['fields'][key]['evidence'] for key in keys if key in event['fields']))})

    flow = facts['checks']['flow']
    if flow['choice'] == 'unknown':
        add('FLOW_EVIDENCE_INCOMPLETE', 'flow', 'review', 'Comparable activity counts are unavailable.',
            ('buys', 'sells'), {'reasons': flow['reasons']})
    else:
        buys, sells = valid['buys']['value'], valid['sells']['value']
        if buys + sells == 0:
            code, text = 'FLOW_NO_ACTIVITY', 'The source reports no buys or sells in this window.'
        elif buys > sells:
            code, text = 'FLOW_BUY_DOMINANT', 'Buy counts exceed sell counts in the same source window.'
        elif buys < sells:
            code, text = 'FLOW_SELL_DOMINANT', 'Sell counts exceed buy counts in the same source window.'
        else:
            code, text = 'FLOW_BALANCED', 'Buy and sell counts are equal in the same source window.'
        values = {'buys': buys, 'sells': sells, 'buy_share': flow['buy_share'], 'window_seconds': flow['required_window_seconds']}
        add(code, 'flow', 'info', text, ('buys', 'sells'), values)
        passed = flow['entry_threshold_met']
        add('ENTRY_BUY_SHARE_MET' if passed else 'ENTRY_BUY_SHARE_BELOW_MIN', 'entry', 'pass' if passed else 'block',
            'Buy share meets the entry minimum.' if passed else 'Buy share does not meet the entry minimum.',
            ('buys', 'sells'), {**values, 'required_buy_share': limits['min_buy_share']})

    ownership = facts['checks']['ownership']
    choice = ownership['choice']
    code, level, text = {
        'unknown': ('OWNERSHIP_EVIDENCE_INCOMPLETE', 'review', 'Holder concentration is missing or its scale is unverified.'),
        'concentrated': ('OWNERSHIP_ABOVE_MAX', 'block', 'Top-ten holder share exceeds the configured concentration limit.'),
        'within_limit': ('OWNERSHIP_WITHIN_LIMIT', 'pass', 'Top-ten holder share is within the configured limit.'),
    }[choice]
    if choice == 'unknown' and not limits['require_ownership']:
        level = 'info'
    add(code, 'ownership', level, text, ('top_10_holder_rate',),
        {'ratio': ownership['ratio'], 'limit': limits['max_top_10_holder_ratio']})

    risk = facts['checks']['risk']
    code, level, text = {
        'unknown': ('RISK_EVIDENCE_INCOMPLETE', 'review', 'The required risk reports are not complete.'),
        'reject': ('RISK_SOURCE_REJECT', 'block', 'At least one valid source report flags a rejecting condition.'),
        'clear': ('RISK_REPORTS_CLEAR', 'pass', 'All required source reports are present and non-rejecting.'),
    }[risk['choice']]
    if risk['choice'] == 'unknown' and not limits['require_risk_reports']:
        level = 'info'
    add(code, 'risk', level, text, risk['inputs'], {'reasons': risk['reasons']})
    for key, minimum in [('market_cap', data_policy.min_market_cap_usd), ('liquidity', data_policy.min_liquidity_usd)]:
        field = valid.get(key)
        if not field or field['unit'] != 'USD':
            level = 'review' if getattr(data_policy, 'require_' + key) else 'info'
            add(key.upper() + '_USD_UNVERIFIED', 'market', level, 'A validated USD value is unavailable for ' + key + '.', (key,))
        else:
            passed = field['value'] >= minimum
            add(key.upper() + ('_MIN_MET' if passed else '_BELOW_MIN'), 'market', 'pass' if passed else 'block',
                key + (' meets ' if passed else ' is below ') + 'the configured USD minimum.', (key,),
                {'value_usd': field['value'], 'minimum_usd': minimum})
    if facts['quarantined_fields']:
        add('SOURCE_FIELDS_REQUIRE_REVIEW', 'data', 'review', 'Some supplied values cannot support a verified fact.',
            values={'eligible': len(valid), 'quarantined': len(facts['quarantined_fields'])})

    for task, record in (native_checks or {}).items():
        if task not in facts['checks']:
            continue
        answer = record.get('answers', {}).get(task)
        if not answer:
            add('MODEL_ANSWER_UNAVAILABLE', task, 'review', 'No recorded native answer is available.', origin='model_record')
            continue
        # A record from another token or field state must not be attached by a
        # caller merely because it carries the same task name. The caller owns
        # observation-ID matching; this report also retains the input hash.
        values = {'model_choice': answer.get('choice'), 'rule_choice': facts['checks'][task]['choice'],
                  'answer_probability': answer.get('answer_probability'), 'record_status': record.get('status')}
        if record.get('status') != 'accepted':
            add('MODEL_ANSWER_REQUIRES_REVIEW', task, 'review', 'The native answer did not pass its recorded acceptance gate.',
                values=values, origin='model_record')
        if answer.get('choice') != facts['checks'][task]['choice']:
            add('MODEL_RULE_DISAGREEMENT', task, 'review', 'The native answer differs from the source-bound rule result.',
                values=values, origin='comparison')
    return {'schema': 'omnia.trading.decision-notes.v1', 'observation_id': event['id'],
            'observation_hash': facts['observation_hash'], 'notes': notes,
            'notes_hash': digest(notes), 'execution_authorized': False}
