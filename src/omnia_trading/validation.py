# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Executable semantics preserve source values and make uncertainty explicit."""
from datetime import datetime, timezone
import math

from .catalog import BY_KEY
from .contracts import timestamp
from .identity import address


def event_time(field):
    """Interpret a known event-time unit; never guess seconds versus milliseconds."""
    value, unit = field['value'], field['unit']
    if unit == 'UTC' and isinstance(value, str):
        return timestamp(value)
    if unit in {'unix_seconds', 'unix_milliseconds'} and type(value) in (int, float) and value > 0:
        return datetime.fromtimestamp(value / (1000 if unit == 'unix_milliseconds' else 1), timezone.utc)
    raise ValueError('unknown_event_time')


def normalized_number(field):
    """Only explicit percentages are rescaled; raw source scales remain unknown."""
    return field['value'] / 100 if field['unit'] in {'percent', '%'} else field['value']


def _unit_family(unit):
    return {'Count': 'count', 'Tokens': 'tokens', 'percent': 'ratio', '%': 'ratio'}.get(unit, unit)


def field_issues(key, field, chain):
    """Return semantic reason codes for one structurally valid datapoint."""
    definition = BY_KEY[key]
    value, unit, kind = field['value'], field['unit'], definition['kind']
    issues = []
    if chain not in definition['chains']:
        issues.append('chain_not_applicable:' + key)
    if unit not in definition['allowed_units']:
        issues.append('ambiguous_unit:' + key)
    window = field['window_seconds']
    if definition['requires_window']:
        if window is None:
            issues.append('missing_window:' + key)
        elif definition['window_seconds'] is not None and window != definition['window_seconds']:
            issues.append('unexpected_window:' + key)
    elif window is not None:
        issues.append('unexpected_window:' + key)
    if value is None:
        return [*issues, 'null_value:' + key]
    expected = {
        'number': type(value) in (int, float),
        'integer': type(value) is int,
        'boolean': type(value) is bool,
        'text': isinstance(value, str) and bool(value.strip()),
        'address': isinstance(value, str),
        'timestamp': isinstance(value, str) or type(value) in (int, float),
    }
    if not expected[kind]:
        return [*issues, 'invalid_kind:' + key]
    if kind in {'number', 'integer'}:
        try:
            finite = math.isfinite(value)
        except (OverflowError, TypeError):
            finite = False
        if not finite:
            return [*issues, 'nonfinite_value:' + key]
        # Catalog bounds for proportions and changes are expressed in ratio units.
        number = normalized_number(field)
        if definition['minimum'] is not None and number < definition['minimum']:
            issues.append('below_domain:' + key)
        if definition['maximum'] is not None and number > definition['maximum']:
            issues.append('above_domain:' + key)
    elif kind == 'address':
        try:
            address(value, chain)
        except (ValueError, TypeError):
            issues.append('invalid_address:' + key)
    elif kind == 'timestamp':
        try:
            value_time = event_time(field)
            if (value_time - timestamp(field['observed_at'])).total_seconds() > 5:
                issues.append('future_event_time:' + key)
        except (ValueError, TypeError, OverflowError, OSError):
            issues.append('unknown_event_time:' + key)
    return issues


def comparable(fields, keys, *, require_window=False):
    """Comparisons require the same source capture, clock, unit and window."""
    if not all(key in fields for key in keys):
        return False
    rows = [fields[key] for key in keys]
    first = rows[0]
    if require_window and first['window_seconds'] is None:
        return False
    return all(_unit_family(row['unit']) == _unit_family(first['unit']) and row['window_seconds'] == first['window_seconds']
               and timestamp(row['observed_at']) == timestamp(first['observed_at'])
               and row['evidence'] == first['evidence'] for row in rows[1:])


def validate_semantics(event):
    """Validate supplied fields only; absent optional fields do not imply coverage."""
    fields, chain = event['fields'], event['identity']['chain']
    by_field = {key: field_issues(key, field, chain) for key, field in fields.items()}
    issues = [issue for values in by_field.values() for issue in values]
    envelope_time = timestamp(event['observed_at'])
    for key, field in fields.items():
        if (timestamp(field['observed_at']) - envelope_time).total_seconds() > 5:
            issues.append('field_after_observation:' + key)
    pairs = (
        ('circulating_supply', 'total_supply'),
        ('top_1_holder_rate', 'top_10_holder_rate'),
        ('unique_buyers', 'buys'),
        ('unique_sellers', 'sells'),
    )
    for lesser, greater in pairs:
        if comparable(fields, (lesser, greater)) and not by_field[lesser] and not by_field[greater]:
            if normalized_number(fields[lesser]) > normalized_number(fields[greater]):
                issues.append('inconsistent_fields:' + lesser + ',' + greater)
    if all(key in fields and not by_field[key] for key in ('start_live_timestamp', 'end_live_timestamp')):
        if event_time(fields['start_live_timestamp']) > event_time(fields['end_live_timestamp']):
            issues.append('inconsistent_fields:start_live_timestamp,end_live_timestamp')
    return list(dict.fromkeys(issues))
