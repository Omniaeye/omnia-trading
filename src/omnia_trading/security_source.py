# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Pure adapter for archived GMGN token-security responses, without network I/O."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re

from .contracts import normalize, timestamp
from .identity import address, identity
from .strategy_facts import RISK_FLAGS
from .validation import field_issues

VERSION = 'omnia.trading.gmgn-security.v1'
REFERENCE = 'https://github.com/GMGNAI/gmgn-skills/blob/main/skills/gmgn-token/SKILL.md'
# Only this endpoint documents these values as fractions. Ranking has a
# different contract; identical names do not authorize a cross-endpoint alias.
RATIOS = ('buy_tax', 'sell_tax', 'top_10_holder_rate', 'dev_team_hold_rate', 'creator_balance_rate')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError('nonfinite_json_number')


def _float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('nonfinite_json_number')
    return number


def _ratio(value):
    if type(value) not in (int, float, str):
        raise ValueError('invalid_ratio_encoding')
    text = str(value)
    if len(text) > 128 or not re.fullmatch(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', text):
        raise ValueError('invalid_ratio_encoding')
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError('invalid_ratio_encoding') from error
    if not number.is_finite() or not 0 <= number <= 1:
        raise ValueError('ratio_out_of_range')
    result = float(number)
    if number and result == 0:
        raise ValueError('ratio_underflow')
    return result


def adapt_security(raw, metadata):
    """Project a hash-bound token response while preserving every original field.

    Metadata binds the request identity and transport clocks. It does not prove
    on-chain existence. Token-level security never inherits a ranking pool ID.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 1024 * 1024:
        raise ValueError('invalid_security_response_size')
    required = {'identity', 'capture_id', 'requested_at', 'received_at', 'sha256'}
    if not isinstance(metadata, dict) or set(metadata) != required:
        raise ValueError('invalid_security_metadata')
    raw_hash = hashlib.sha256(raw).hexdigest()
    if metadata['sha256'] != raw_hash:
        raise ValueError('hash_mismatch')
    capture_id = metadata['capture_id']
    if not isinstance(capture_id, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,96}', capture_id):
        raise ValueError('invalid_capture_id')
    asset = identity(metadata['identity'])
    if asset['pool'] is not None:
        raise ValueError('token_scope_requires_null_pool')
    if timestamp(metadata['requested_at']) > timestamp(metadata['received_at']):
        raise ValueError('invalid_capture_clock')
    payload = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant, parse_float=_float)
    if not isinstance(payload, dict):
        raise ValueError('invalid_security_response')
    if address(payload.get('address'), asset['chain']) != asset['contract']:
        raise ValueError('identity_mismatch')
    if 'chain' in payload:
        response_chain = 'solana' if payload['chain'] == 'sol' else payload['chain']
        if response_chain != asset['chain']:
            raise ValueError('chain_mismatch')
    evidence = 'capture:' + capture_id + ':sha256:' + raw_hash
    fields, unprojected = {}, {}
    for key, value in payload.items():
        if key in ('address', 'chain'):
            continue
        reason = 'no_reviewed_endpoint_mapping'
        parsed, unit = None, None
        if key in RATIOS:
            try:
                parsed, unit = _ratio(value), 'ratio'
            except ValueError as error:
                reason = str(error)
        elif key == 'is_honeypot':
            if asset['chain'] != 'bsc':
                reason = 'source_honeypot_coverage_not_established_for_chain'
            elif type(value) is bool:
                # Native bool was observed in bounded CLI captures; older docs
                # specify yes/no. Integer aliases remain unreviewed.
                parsed, unit = value, 'boolean'
            elif type(value) is str and value in ('yes', 'no'):
                parsed, unit = value == 'yes', 'boolean'
            else:
                reason = 'missing_or_unrecognized_security_boolean'
        elif key in ('renounced_mint', 'renounced_freeze_account'):
            if asset['chain'] != 'solana':
                reason = 'authority_flag_not_applicable_to_chain'
            elif type(value) is bool:
                parsed, unit = value, 'boolean'
            else:
                reason = 'missing_or_unrecognized_security_boolean'
        elif key == 'is_wash_trading':
            if type(value) is bool:
                parsed, unit = value, 'boolean'
            else:
                reason = 'missing_or_unrecognized_security_boolean'
        elif key in ('can_sell', 'can_not_sell'):
            reason = 'sentinel_not_a_source_sell_simulation_receipt'
        elif key == 'transfer_pausable':
            reason = 'pause_capability_is_not_current_pause_state'
        if unit is not None:
            field = {'value': parsed, 'unit': unit, 'window_seconds': None,
                     'observed_at': metadata['received_at'], 'evidence': evidence}
            issues = field_issues(key, field, asset['chain'])
            if not issues:
                fields[key] = field
                continue
            reason = ','.join(issues)
        unprojected[key] = {'value': deepcopy(value), 'reason': reason}
    observation = normalize({'id': 'security:' + capture_id, 'source': 'gmgn.token_security',
                             'identity': asset, 'observed_at': metadata['received_at'], 'fields': fields}) if fields else None
    return {'schema': VERSION, 'status': 'projected' if observation else 'insufficient',
            'observation': observation, 'source_payload': payload, 'source_sha256': raw_hash,
            'metadata': deepcopy(metadata), 'source_reference': REFERENCE,
            'unprojected_fields': unprojected, 'unavailable_strategy_fields': [key for key in RISK_FLAGS if key not in fields],
            'execution_authorized': False}
