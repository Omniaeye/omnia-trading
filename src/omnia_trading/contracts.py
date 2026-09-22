# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Observations retain timestamps, units, windows and evidence per field."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from .catalog import BY_KEY
from .identity import identity


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp_required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone_required')
    return parsed.astimezone(timezone.utc)


def normalize(event, max_bytes=65536):
    if not isinstance(event, dict) or set(event) != {'id', 'source', 'observed_at', 'identity', 'fields'}:
        raise ValueError('invalid_observation_fields')
    if len(json.dumps(event, ensure_ascii=False, allow_nan=False).encode()) > max_bytes:
        raise ValueError('observation_too_large')
    for name in ('id', 'source'):
        if not isinstance(event[name], str) or not event[name].strip() or len(event[name]) > 200:
            raise ValueError('invalid_identifier')
    out = deepcopy(event)
    out['identity'] = identity(out['identity'])
    timestamp(out['observed_at'])
    if not isinstance(out['fields'], dict) or not out['fields'] or set(out['fields']) - set(BY_KEY):
        raise ValueError('unknown_or_empty_fields')
    for field in out['fields'].values():
        if not isinstance(field, dict) or set(field) != {'value', 'unit', 'window_seconds', 'observed_at', 'evidence'}:
            raise ValueError('invalid_datapoint_fields')
        value = field['value']
        if value is not None and type(value) not in (bool, int, float, str):
            raise ValueError('invalid_scalar')
        if type(value) in (int, float) and not math.isfinite(value):
            raise ValueError('nonfinite_value')
        if isinstance(value, str) and len(value) > 2048:
            raise ValueError('value_too_long')
        for name, size in (('unit', 64), ('evidence', 512)):
            if not isinstance(field[name], str) or not field[name].strip() or len(field[name]) > size:
                raise ValueError('invalid_field_metadata')
        window = field['window_seconds']
        if window is not None and (type(window) is not int or not 1 <= window <= 2592000):
            raise ValueError('invalid_window')
        timestamp(field['observed_at'])
    return out
