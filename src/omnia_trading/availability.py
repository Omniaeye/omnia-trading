# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Separate absent source values from malformed reported measurements."""
from .catalog import BY_KEY


def reported_observation(event):
    fields, excluded = {}, {}
    for key, field in event['fields'].items():
        if event['identity']['chain'] not in BY_KEY[key]['chains']:
            excluded[key] = 'not_applicable'
        elif field['value'] is None:
            excluded[key] = 'not_reported'
        else:
            fields[key] = field
    return {**event, 'fields': fields}, excluded
