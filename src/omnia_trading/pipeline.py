# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Evaluate each populated parameter group while preserving every observation."""
from dataclasses import asdict
from .catalog import group_fields
from .contracts import normalize
from .policy import Policy, evaluate
from .questions import QUESTIONS, TASK_VERSION
from ._engine.ledger import digest


def process(event, ledger, backend, *, min_probability=.8, max_bytes=65536, policy=None, now=None):
    item = normalize(event, max_bytes)
    policy = policy or Policy()
    disposition, reasons = evaluate(item, policy, now)
    records, failures = {}, {}
    if disposition != 'skip':
        manifest = {**backend.manifest(), 'task': TASK_VERSION, 'source_hash': digest(item), 'policy': asdict(policy)}
        for group, fields in group_fields(item['fields']).items():
            if not fields:
                continue
            request = {'id': 'observation:' + digest({'id': item['id'], 'group': group}),
                       'state': {'group': group, 'fields': {key: {k: f[k] for k in ('value', 'unit', 'window_seconds')}
                                                        for key, f in fields.items()}},
                       'questions': QUESTIONS, 'evidence': list(dict.fromkeys(f['evidence'] for f in fields.values()))}
            try:
                records[group] = ledger.decide(request, backend, manifest=manifest,
                                               min_probability=min_probability, max_bytes=max_bytes)
            except Exception as error:
                failures[group] = type(error).__name__
        if failures:
            disposition, reasons = 'review', [*reasons, 'group_processing_failed']
        elif any(r['status'] != 'accepted' or r['answers']['quality']['choice'] != 'usable' for r in records.values()):
            disposition, reasons = 'review', [*reasons, 'group_requires_review']
        elif disposition == 'observe':
            disposition = 'candidate'
    return {'schema': 'omnia.trading.assessment.v1', 'observation_id': item['id'],
            'identity': item['identity'], 'observation_hash': digest(item), 'parameter_count': len(item['fields']),
            'disposition': disposition, 'reasons': reasons, 'groups': records, 'group_failures': failures,
            'execution_authorized': False, 'task_version': TASK_VERSION}
