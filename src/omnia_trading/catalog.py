# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""The product catalog preserves source units and explicit unknowns."""
from importlib.resources import files
import hashlib
import json

CATALOG_VERSION = 'omnia.trading.parameters.v2'
_catalog_text = files(__package__).joinpath('parameters.json').read_text(encoding='utf-8')
PARAMETERS = json.loads(_catalog_text)
CATALOG_SHA256 = hashlib.sha256(_catalog_text.encode('utf-8')).hexdigest()
BY_KEY = {row['key']: row for row in PARAMETERS}
GROUPS = ('Market', 'Holders', 'Risk', 'Lifecycle', 'Social')


def group_fields(fields):
    return {group: {key: value for key, value in fields.items() if BY_KEY[key]['group'] == group}
            for group in GROUPS}
