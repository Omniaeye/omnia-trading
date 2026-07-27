# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Evaluate each populated parameter group while preserving every observation."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from .catalog import BY_KEY, CATALOG_SHA256, CATALOG_VERSION, group_fields
from .contracts import normalize, timestamp
from .features import derive_metrics
from .policy import POLICY_VERSION, Policy, evaluate
from .questions import QUESTIONS, TASK_VERSION
from ._engine.ledger import digest, probability

MAX_FIELDS_PER_ASSESSMENT = 4


def _utcnow():
    return datetime.now(timezone.utc)


def _valid_until(item, policy):
    oldest = min(timestamp(item['observed_at']), *(timestamp(f['observed_at']) for f in item['fields'].values()))
    try:
        return (oldest + timedelta(seconds=policy.max_age_seconds)).isoformat()
    except OverflowError:
        return datetime.max.replace(tzinfo=timezone.utc).isoformat()


def _state(item, group, fields):
    # Relative field clocks retain temporal context without repeating long ISO strings.
    envelope_time = timestamp(item['observed_at'])
    return {'context': {'identity': item['identity'], 'source': item['source'], 'observed_at': item['observed_at']},
            'group': group,
            'fields': {key: {**{k: field[k] for k in ('value', 'unit', 'window_seconds')},
                             'observed_offset_seconds': (timestamp(field['observed_at']) - envelope_time).total_seconds()}
                       for key, field in fields.items()}}


def _batches(item):
    """Stable bounded partitions cover every supplied field exactly once."""
    for group, fields in group_fields(item['fields']).items():
        keys = sorted(fields)
        chunks = [keys[start:start + MAX_FIELDS_PER_ASSESSMENT]
                  for start in range(0, len(keys), MAX_FIELDS_PER_ASSESSMENT)]
        for index, chunk in enumerate(chunks, 1):
            name = group if len(chunks) == 1 else group + ':part' + str(index)
            yield name, group, {key: fields[key] for key in chunk}, index, len(chunks)


def process(event, ledger, backend, *, min_probability=.8, max_bytes=65536, policy=None, now=None):
    item = normalize(event, max_bytes)
    policy = policy or Policy()
    floor = probability(min_probability)
    started_at = _utcnow() if now is None else now
    disposition, reasons = evaluate(item, policy, started_at)
    records, failures, batch_map = {}, {}, {}
    if disposition != 'skip':
        batches = list(_batches(item))
        batch_map = {name: {'group': group, 'fields': list(fields), 'part': index, 'part_count': count}
                     for name, group, fields, index, count in batches}
        try:
            manifest = {**backend.manifest(), 'task': TASK_VERSION, 'source_hash': digest(item),
                        'catalog_sha256': CATALOG_SHA256, 'policy_version': POLICY_VERSION, 'policy': asdict(policy)}
        except Exception as error:
            failures = {name: type(error).__name__ for name in batch_map}
        else:
            for name, group, fields, index, count in batches:
                request = {'id': 'observation:' + digest({'id': item['id'], 'group': group,
                                                        'part': index, 'fields': list(fields)}),
                           'state': _state(item, group, fields), 'questions': QUESTIONS,
                           'evidence': list(dict.fromkeys(f['evidence'] for f in fields.values()))}
                try:
                    record = ledger.decide(request, backend, manifest=manifest,
                                           min_probability=floor, max_bytes=max_bytes)
                    records[name] = {**record, 'batch': batch_map[name]}
                except Exception as error:
                    failures[name] = type(error).__name__
        if failures:
            disposition, reasons = 'review', [*reasons, 'group_processing_failed']
        elif any(r['status'] != 'accepted' or r['answers']['quality']['choice'] != 'usable' for r in records.values()):
            disposition, reasons = 'review', [*reasons, 'group_requires_review']
    evaluated_at = _utcnow() if now is None else now
    final_disposition, final_reasons = evaluate(item, policy, evaluated_at)
    reasons = list(dict.fromkeys([*reasons, *final_reasons]))
    if final_disposition == 'skip':
        disposition = 'skip'
    elif final_disposition == 'review':
        disposition = 'review'
    elif disposition == 'observe':
        disposition = 'candidate'
    result = {'schema': 'omnia.trading.assessment.v1', 'observation_id': item['id'], 'source': item['source'],
              'identity': item['identity'], 'observed_at': item['observed_at'],
              'observation_hash': digest(item), 'parameter_count': len(item['fields']),
              'evidence': list(dict.fromkeys(field['evidence'] for field in item['fields'].values())),
              'evaluation_started_at': started_at.astimezone(timezone.utc).isoformat(),
              'evaluated_at': evaluated_at.astimezone(timezone.utc).isoformat(),
              'clock_mode': 'realtime' if now is None else 'replay', 'valid_until': _valid_until(item, policy),
              'policy': {'version': POLICY_VERSION, 'configuration': asdict(policy), 'min_answer_probability': floor},
              'catalog_version': CATALOG_VERSION, 'catalog_sha256': CATALOG_SHA256,
              'disposition': disposition, 'reasons': reasons, 'groups': records, 'group_failures': failures,
              'assessment_batches': batch_map,
              'deterministic_metrics': derive_metrics(item, reasons),
              'field_notes': {key: BY_KEY[key]['note'] for key in item['fields']},
              'notes': ['Catalog support does not establish collection coverage or independent verification.',
                        'Candidate is a data-policy result, not a trading signal or a security guarantee.',
                        'Derived metrics describe aligned source aggregates; they do not identify individual trades.',
                        'Consumers must check valid_until against their own clock before using a realtime assessment.'],
              'execution_authorized': False, 'task_version': TASK_VERSION}
    return ledger.record_assessment(result)
