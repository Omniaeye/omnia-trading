# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Build a private, static report from hash-verified archived ranking captures."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from importlib.resources import files

from .capture_archive import asset_key, ranking_series
from .casebook import validate_native_records
from .performance import summarize_quotes
from .strategy_contracts import StrategyPolicy
from .strategy_facts import assess_facts
from .policy import Policy, evaluate
from .contracts import normalize, timestamp
from .decision_notes import explain_observation


def build(source: Path, output: Path):
    manifest = json.loads((source / 'manifest.json').read_bytes())
    sample_bytes = (source / 'sample.json').read_bytes()
    freeze_path = source / 'sample-freeze.json'
    if freeze_path.exists():
        freeze = json.loads(freeze_path.read_bytes())
        if hashlib.sha256(sample_bytes).hexdigest() != freeze['sample_sha256']:
            raise ValueError('sample_freeze_hash_mismatch')
    sample = json.loads(sample_bytes)
    ids = [entry['event']['id'] for entry in sample]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate_sample_observation')
    native_path = source / 'task-results.jsonl'
    native = {}
    for line in native_path.read_text(encoding='utf-8').splitlines():
        record = json.loads(line)
        if record['observation_id'] in native:
            raise ValueError('duplicate_native_observation')
        native[record['observation_id']] = record
    calls_path = source / 'task-model-calls.jsonl'
    if calls_path.exists():
        calls = [json.loads(line) for line in calls_path.read_text(encoding='utf-8').splitlines() if line]
        validate_native_records(sample, list(native.values()), calls)
    native_summary_path = source / 'task-summary.json'
    native_summary = json.loads(native_summary_path.read_bytes()) if native_summary_path.exists() else {}
    groups, issues, verified_hashes = ranking_series(source, manifest)
    for entry in sample:
        event = normalize(entry['event'])
        key = asset_key(event['identity'])
        if key not in groups:
            groups[key] = {'id': hashlib.sha256(key.encode()).hexdigest()[:20], 'identity': event['identity'],
                           'name': str(entry['name'])[:100], 'source': entry['endpoint'], 'points': [], 'evaluations': []}
        facts = assess_facts(event, now=timestamp(event['observed_at']))
        disposition, reasons = evaluate(event, Policy(), timestamp(event['observed_at']))
        # This is the existing entry precheck, not a fabricated account snapshot
        # or a call to the full position strategy.
        gate = 'SKIP' if disposition != 'observe' or facts['checks']['risk']['choice'] == 'reject' else 'NEEDS_CONTEXT'
        record = native.get(event['id'], {})
        if record and record.get('identity') != event['identity']:
            raise ValueError('native_identity_mismatch')
        notes = explain_observation(event, now=timestamp(event['observed_at']),
                                    native_checks=record.get('task_checks', {}))
        if any(note['level'] == 'block' for note in notes['notes']):
            gate = 'SKIP'
        answers = {task: {'choice': item.get('answers', {}).get(task, {}).get('choice'),
                          'probability': item.get('answers', {}).get(task, {}).get('answer_probability'),
                          'status': item.get('status')} for task, item in record.get('task_checks', {}).items()}
        groups[key]['evaluations'].append({'at': event['observed_at'], 'observation_id': event['id'],
                                          'gate': gate, 'reasons': reasons,
                                          'risk_reasons': facts['checks']['risk']['reasons'],
                                          'facts': {task: item['choice'] for task, item in facts['checks'].items()},
                                          'decision_notes': notes,
                                          'native_laya': answers, 'full_strategy_executed': False})
    rows = []
    for group in groups.values():
        try:
            group['performance'] = summarize_quotes(group['points'])
        except ValueError as error:
            group['performance'] = {'status': str(error), 'market': None, 'scenario': None}
            issues.append({'series': group['id'], 'reason': str(error)})
        rows.append(group)
    rows.sort(key=lambda row: (row['performance']['market'] or {}).get('return_ratio', -math.inf), reverse=True)
    observed = [row for row in rows if row['performance']['market']]
    events = Counter(e['action'] for row in observed for e in row['performance']['scenario']['events'])
    gates = Counter(e['gate'] for row in rows for e in row['evaluations'])
    summary = {'series_count': len(rows), 'rank_series_count': sum(row['source'] == 'market_rank' for row in rows),
               'price_series_with_two_quotes': len(observed), 'evaluated_observations': sum(len(row['evaluations']) for row in rows),
               'observed_2x': sum(row['performance']['market']['milestones']['2'] is not None for row in observed),
               'final_2x': sum(row['performance']['market']['final_multiple'] >= 2 for row in observed),
               'entry_gates': dict(gates), 'scenario_events': dict(events), 'executed_orders': 0,
               'actual_profit_usd': None, 'capture_start': manifest['started_at'], 'capture_end': manifest['ended_at'],
               'capture_duration_seconds': manifest['duration_seconds'],
               'fees_slippage_included': False, 'issues': issues,
               'policy': {key: getattr(StrategyPolicy(), key) for key in StrategyPolicy.__dataclass_fields__}}
    summary['native_task_metrics'] = {
        task: {key: value for key, value in metrics.items() if key != 'rows'}
        for task, metrics in native_summary.get('task_metrics', {}).items()}
    summary['native_model'] = native_summary.get('backend')
    result = {'schema': 'omnia.trading.performance-report.v1', 'summary': summary, 'rows': rows,
              'input_sha256': {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                               for name in ('manifest.json', 'sample.json', 'task-results.jsonl')},
              'capture_sha256': verified_hashes, 'publication_authorized': False}
    for name in ('task-summary.json', 'sample-freeze.json', 'expected-before-model.json'):
        if (source / name).exists():
            result['input_sha256'][name] = hashlib.sha256((source / name).read_bytes()).hexdigest()
    package = files(__package__)
    result['implementation_sha256'] = {
        name: hashlib.sha256(package.joinpath(name).read_bytes()).hexdigest()
        for name in ('capture_archive.py', 'casebook.py', 'reporting.py', 'performance.py',
                     'decision_notes.py', 'strategy_facts.py', 'strategy_contracts.py',
                     'contracts.py', 'policy.py', 'identity.py', 'availability.py', 'parameters.json')}
    output.mkdir(parents=True, exist_ok=False)
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=True, allow_nan=False), encoding='utf-8')
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    arguments = parser.parse_args()
    build(arguments.capture_dir, arguments.output_dir)
