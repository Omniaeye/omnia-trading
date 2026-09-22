# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""The product catalog preserves source units and explicit unknowns."""
from importlib.resources import files
import json

PARAMETERS = json.loads(files(__package__).joinpath('parameters.json').read_text(encoding='utf-8'))
BY_KEY = {row['key']: row for row in PARAMETERS}
GROUPS = ('Market', 'Holders', 'Risk', 'Lifecycle', 'Social')


def group_fields(fields):
    return {group: {key: value for key, value in fields.items() if BY_KEY[key]['group'] == group}
            for group in GROUPS}
