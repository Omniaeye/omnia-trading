# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Build a private, static report from hash-verified archived ranking captures."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from omnia_trading.identity import identity
from omnia_trading.performance import summarize_quotes
from omnia_trading.strategy_contracts import StrategyPolicy
from omnia_trading.strategy_facts import assess_facts
from omnia_trading.policy import Policy, evaluate
from omnia_trading.contracts import normalize
from omnia_trading.decision_notes import explain_observation


def asset_key(asset):
    return json.dumps(asset, sort_keys=True)


def build(source, output):
    manifest = json.loads((source / 'manifest.json').read_bytes())
    sample = json.loads((source / 'sample.json').read_bytes())
    native_path = source / 'task-results.jsonl'
    native = {}
    for line in native_path.read_text(encoding='utf-8').splitlines():
        record = json.loads(line)
        if record['observation_id'] in native:
            raise ValueError('duplicate_native_observation')
        native[record['observation_id']] = record
    native_summary_path = source / 'task-summary.json'
    native_summary = json.loads(native_summary_path.read_bytes()) if native_summary_path.exists() else {}
    groups, issues = {}, []
    receipts = sorted(manifest['captures'], key=lambda item: item['received_at'])
    verified_hashes = {}
    for receipt in receipts:
        if receipt['endpoint'] != 'market_rank':
            continue
        capture_id = receipt['capture_id']
        raw_path = source / 'raw' / (capture_id + '.json')
        if raw_path.resolve().parent != (source / 'raw').resolve():
            raise ValueError('invalid_capture_path')
        raw = raw_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != receipt['raw_sha256']:
            raise ValueError('capture_hash_mismatch')
        verified_hashes[capture_id] = digest
        payload = json.loads(raw)
        if payload.get('code') != 0:
            raise ValueError('capture_provider_error')
        data = payload['data']
        if isinstance(data, dict) and 'code' in data:
            if data['code'] != 0:
                raise ValueError('capture_provider_error')
            data = data['data']
        chain = 'solana' if receipt['chain'] == 'sol' else receipt['chain']
        for index, token in enumerate(data['rank']):
            try:
                token_chain = 'solana' if token.get('chain') == 'sol' else token.get('chain', chain)
                if token_chain != chain:
                    raise ValueError('source_chain_mismatch')
                asset = identity({'chain': chain, 'network_id': 'provider.' + chain,
                                  'contract': token['address'], 'pool': token.get('pool_address') or None})
                price = token.get('price')
                if type(price) not in (int, float) or not math.isfinite(price) or price <= 0:
                    raise ValueError('unusable_source_price')
                key = asset_key(asset)
                if key not in groups:
                    groups[key] = {'id': hashlib.sha256(key.encode()).hexdigest()[:20], 'identity': asset,
                                   'name': str(token.get('symbol') or token.get('name') or 'Token')[:100],
                                   'source': 'market_rank', 'points': [], 'evaluations': []}
                groups[key]['points'].append({'at': receipt['received_at'], 'price': price,
                                             'evidence': 'capture:' + capture_id + ':rank:' + str(index),
                                             'capture_id': capture_id})
            except (ValueError, KeyError) as error:
                issues.append({'capture_id': capture_id, 'row': index, 'reason': str(error)})
    for entry in sample:
        event = normalize(entry['event'])
        key = asset_key(event['identity'])
        if key not in groups:
            groups[key] = {'id': hashlib.sha256(key.encode()).hexdigest()[:20], 'identity': event['identity'],
                           'name': str(entry['name'])[:100], 'source': entry['endpoint'], 'points': [], 'evaluations': []}
        facts = assess_facts(event, now=datetime.fromisoformat(event['observed_at']))
        disposition, reasons = evaluate(event, Policy(), datetime.fromisoformat(event['observed_at']))
        # This is the existing entry precheck, not a fabricated account snapshot
        # or a call to the full position strategy.
        gate = 'SKIP' if disposition != 'observe' or facts['checks']['risk']['choice'] == 'reject' else 'NEEDS_CONTEXT'
        record = native.get(event['id'], {})
        if record and record.get('identity') != event['identity']:
            raise ValueError('native_identity_mismatch')
        notes = explain_observation(event, now=datetime.fromisoformat(event['observed_at']),
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
    root = Path(__file__).resolve().parents[1]
    result['implementation_sha256'] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ('tools/build_performance_report.py', 'tools/performance_report.html',
                     'src/omnia_trading/performance.py', 'src/omnia_trading/decision_notes.py',
                     'src/omnia_trading/strategy_facts.py', 'src/omnia_trading/strategy_contracts.py',
                     'src/omnia_trading/contracts.py', 'src/omnia_trading/policy.py',
                     'src/omnia_trading/identity.py', 'src/omnia_trading/availability.py',
                     'src/omnia_trading/parameters.json')}
    output.mkdir(parents=True, exist_ok=False)
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=True, allow_nan=False), encoding='utf-8')
    shutil.copyfile(Path(__file__).with_name('performance_report.html'), output / 'index.html')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    arguments = parser.parse_args()
    build(arguments.capture_dir, arguments.output_dir)
