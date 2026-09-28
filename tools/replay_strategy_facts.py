# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Compare immutable capture samples, expected labels and recorded native inference."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from omnia_trading.strategy_facts import assess_facts


def indexed(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError('duplicate_observation_id')
        result[value] = row
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample', required=True, type=Path)
    parser.add_argument('--expected', required=True, type=Path)
    parser.add_argument('--model-results', action='append', default=[], type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()
    sample_bytes = args.sample.read_bytes()
    sample = json.loads(sample_bytes)
    expected = indexed(json.loads(args.expected.read_bytes()), 'observation_id')
    ids = [row['event']['id'] for row in sample]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError('sample_expected_identity_mismatch')
    models = []
    for path in args.model_results:
        rows = indexed([json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line], 'observation_id')
        if set(rows) != set(ids):
            raise ValueError('model_sample_identity_mismatch')
        models.append((str(path), rows))
    args.out_dir.mkdir(parents=True, exist_ok=False)
    counts, quarantine, choices = Counter(), Counter(), {task: Counter() for task in ('risk', 'flow', 'ownership')}
    mismatches, results = [], []
    agreement = Counter()
    model_metrics = {name: {'comparisons': 0, 'disagreements': 0, 'accepted_disagreements': 0} for name, _ in models}
    for row in sample:
        event, identifier = row['event'], row['event']['id']
        result = {'observation_id': identifier}
        try:
            facts = assess_facts(event, now=datetime.fromisoformat(event['observed_at']))
            result['facts'] = facts
            counts['normalized_observations'] += 1
            counts['fields'] += len(event['fields'])
            counts['eligible_fields'] += len(facts['eligible_fields'])
            counts['quarantined_fields'] += len(facts['quarantined_fields'])
            counts['chain:' + event['identity']['chain']] += 1
            quarantine.update(reason for item in facts['quarantined_fields'].values() for reason in item['reasons'])
            for task, check in facts['checks'].items():
                actual = check['choice']
                choices[task][actual] += 1
                if actual == expected[identifier][task]:
                    agreement[task] += 1
                else:
                    mismatches.append({'observation_id': identifier, 'task': task,
                                       'expected': expected[identifier][task], 'actual': actual})
                for name, records in models:
                    record = records[identifier]['task_checks'][task]
                    answer = record.get('answers', {}).get(task, {})
                    if 'choice' not in answer:
                        continue
                    metrics = model_metrics[name]
                    metrics['comparisons'] += 1
                    if answer['choice'] != actual:
                        metrics['disagreements'] += 1
                        metrics['accepted_disagreements'] += int(record.get('status') == 'accepted')
        except (ValueError, KeyError, TypeError) as error:
            counts['errors'] += 1
            result['error'] = {'type': type(error).__name__, 'message': str(error)}
        results.append(result)
    sources = [args.sample, args.expected, *args.model_results]
    summary = {'schema': 'omnia.trading.facts-replay.v1', 'sample_count': len(sample), 'counts': dict(counts),
               'sample_sha256': hashlib.sha256(sample_bytes).hexdigest(),
               'input_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
               'facts_agreement_with_frozen_expected': dict(agreement), 'facts_disagreements': mismatches,
               'choices': {key: dict(value) for key, value in choices.items()},
               'quarantine_reasons': dict(quarantine), 'recorded_model_comparison': model_metrics,
               'new_model_calls': 0, 'execution_authorized': False, 'publication_authorized': False,
               'quality_scope': 'Deterministic rule agreement; not model precision or trade performance.'}
    (args.out_dir / 'results.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=True) + '\n' for row in results), encoding='utf-8')
    (args.out_dir / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in summary.items() if key not in ('input_sha256', 'quarantine_reasons')}, indent=2))
    return 1 if counts['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
