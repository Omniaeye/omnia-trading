# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Publish and verify a complete capture window without rerunning inference."""
import argparse
from copy import deepcopy
from collections import Counter
import csv
import hashlib
import html
import json
from pathlib import Path
import re

from ._engine.ledger import digest
from .contracts import normalize, timestamp
from .capture_archive import asset_key, ranking_series
from .performance import summarize_quotes
from .strategy_contracts import StrategyPolicy
from .casebook_views import token_groups, write_tokens

SCHEMA = 'omnia.trading.casebook.v1'


def _read(path):
    return json.loads(path.read_bytes())


def _lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def _jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=True, allow_nan=False) + '\n' for row in rows), encoding='utf-8', newline='\n')


def _index(rows, key):
    result = {}
    for row in rows:
        identifier = row[key]
        if identifier in result:
            raise ValueError('duplicate_record:' + key)
        result[identifier] = row
    return result


def _csv(path, columns, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            safe = {}
            for key in columns:
                value = row.get(key)
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=True)
                # Spreadsheet formulas must never execute from token names or source values.
                if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                    value = "'" + value
                safe[key] = value
            writer.writerow(safe)


def _md(value):
    return html.escape(str(value)).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ').replace('`', '&#96;')


def validate_native_records(samples, decisions, calls):
    """Bind stored native responses to source fields, question order and acceptance gates."""
    expected_ids = {row['event']['id'] for row in samples}
    if len(expected_ids) != len(samples):
        raise ValueError('duplicate_sample_observation')
    native = _index(decisions, 'observation_id')
    if set(native) != expected_ids:
        raise ValueError('native_cohort_mismatch')
    indexed_calls = {}
    for call in calls:
        key = (call['observation_id'], call['state']['task'])
        if key in indexed_calls:
            raise ValueError('duplicate_native_call')
        indexed_calls[key] = call
    used = set()
    for entry in samples:
        event = normalize(entry['event'])
        record = native[event['id']]
        if event['identity'] != record['identity']:
            raise ValueError('native_identity_mismatch')
        for task, decision in record['task_checks'].items():
            key = (event['id'], task)
            if key not in indexed_calls:
                raise ValueError('native_call_missing')
            used.add(key)
            call = indexed_calls[key]
            if digest(call['state']) != decision['input_sha256']:
                raise ValueError('native_input_hash_mismatch')
            order = [(name, list(question['criteria'])) for name, question in call['questions'].items()]
            if digest({'questions': call['questions'], 'order': order}) != decision['questions_sha256']:
                raise ValueError('native_question_hash_mismatch')
            if call['state']['chain'] != event['identity']['chain']:
                raise ValueError('native_chain_mismatch')
            for name, field in call['state']['fields'].items():
                actual = event['fields'].get(name)
                if actual is None or digest(field) != digest({k: actual[k] for k in ('value', 'unit', 'window_seconds')}):
                    raise ValueError('native_field_mismatch')
            answer = call['response']['answers'][task]
            saved = decision['answers'][task]
            if answer['choice'] != saved['choice'] or answer['probabilities'] != saved['probabilities']:
                raise ValueError('native_answer_mismatch')
            probability = saved['probabilities'][saved['choice']]
            reviewed = [task] if probability < decision['policy']['min_answer_probability'] else []
            if saved['answer_probability'] != probability or decision['review_questions'] != reviewed:
                raise ValueError('native_acceptance_mismatch')
            if decision['status'] != ('review' if reviewed else 'accepted'):
                raise ValueError('native_acceptance_mismatch')
    if used != set(indexed_calls):
        raise ValueError('extra_native_call')


def _validate_series(rows):
    _index(rows, 'id')
    for row in rows:
        if not isinstance(row['id'], str) or re.fullmatch(r'[a-f0-9]{20}', row['id']) is None:
            raise ValueError('invalid_series_id')
        if row['identity']['chain'] not in ('robinhood', 'bsc', 'solana'):
            raise ValueError('unsupported_series_chain')


def _verify_parameter_sources(capture, samples, receipts):
    by_id = _index(receipts, 'capture_id')
    for entry in samples:
        event = entry['event']
        capture_id = event['id'].split(':', 1)[0]
        receipt = by_id.get(capture_id)
        if receipt is None or receipt['raw_sha256'] != entry['raw_hash']:
            raise ValueError('observation_capture_mismatch')
        if timestamp(event['observed_at']) != timestamp(receipt['received_at']):
            raise ValueError('observation_capture_time_mismatch')
        raw = _read(capture / 'raw' / (capture_id + '.json'))
        if set(event['fields']) != set(entry['mappings']):
            raise ValueError('parameter_mapping_coverage_mismatch')
        for name, field in event['fields'].items():
            mapping = entry['mappings'][name]
            value = raw
            for part in mapping['path'].split('/')[1:]:
                key = part.replace('~1', '/').replace('~0', '~')
                value = value[int(key)] if isinstance(value, list) else value[key]
            projected = value
            if (mapping.get('transform') == 'explicit_source_contract'
                    and mapping.get('source_contract_verified') is True
                    and mapping.get('contract_reason') == 'provider_integer_flag_not_independent_security_verdict'
                    and name in {'is_renounced', 'is_open_source', 'is_honeypot', 'renounced_mint', 'renounced_freeze_account'}
                    and field['unit'] == 'boolean' and type(value) is int and value in (0, 1)):
                projected = bool(value)
            if digest(value) != digest(mapping['source_value']) or digest(projected) != digest(field['value']):
                raise ValueError('parameter_source_value_mismatch')


def _verify_report_sources(capture, manifest, samples, report):
    groups, _, hashes = ranking_series(capture, manifest)
    if hashes != report['capture_sha256']:
        raise ValueError('report_capture_coverage_mismatch')
    actual = {asset_key(row['identity']): row for row in report['rows']}
    expected = set(groups) | {asset_key(row['event']['identity']) for row in samples}
    if len(actual) != len(report['rows']) or set(actual) != expected:
        raise ValueError('report_series_coverage_mismatch')
    for key, row in actual.items():
        if row['points'] != groups.get(key, {}).get('points', []):
            raise ValueError('report_quote_source_mismatch')
        if row['id'] != hashlib.sha256(key.encode()).hexdigest()[:20]:
            raise ValueError('report_series_identity_mismatch')
    for field, source_field in (('capture_start', 'started_at'), ('capture_end', 'ended_at'),
                                ('capture_duration_seconds', 'duration_seconds')):
        if report['summary'][field] != manifest[source_field]:
            raise ValueError('report_capture_window_mismatch')


def _metrics(decisions):
    result = {}
    for record in decisions:
        for task, check in record['task_checks'].items():
            metric = result.setdefault(task, {'answered': 0, 'agreement': 0, 'accepted': 0, 'accepted_wrong': 0})
            matches = check['answers'][task]['choice'] == record['expected'][task]
            accepted = check['status'] == 'accepted'
            metric['answered'] += 1
            metric['agreement'] += int(matches)
            metric['accepted'] += int(accepted)
            metric['accepted_wrong'] += int(accepted and not matches)
    return result


def verify(directory: Path):
    """Check file integrity, model/input binding and every published price replay."""
    manifest = _read(directory / 'manifest.json')
    if manifest.get('schema') != SCHEMA:
        raise ValueError('unsupported_casebook_schema')
    for name, checksum in manifest['files'].items():
        path = (directory / name).resolve()
        if directory.resolve() not in path.parents:
            raise ValueError('unsafe_casebook_path')
        if _hash(path) != checksum:
            raise ValueError('casebook_hash_mismatch:' + name)
    actual_files = {path.relative_to(directory).as_posix() for path in directory.rglob('*')
                    if path.is_file() and path != directory / 'manifest.json'}
    if actual_files != set(manifest['files']):
        raise ValueError('casebook_file_set_mismatch')
    observations = _lines(directory / 'observations.jsonl')
    decisions = _lines(directory / 'native-decisions.jsonl')
    calls = _lines(directory / 'native-calls.jsonl')
    validate_native_records(observations, decisions, calls)
    summary = _read(directory / 'summary.json')
    if _metrics(decisions) != summary['native_task_metrics']:
        raise ValueError('native_metrics_mismatch')
    series = _lines(directory / 'series.jsonl')
    _validate_series(series)
    policy = StrategyPolicy(**summary['policy'])
    for row in series:
        if summarize_quotes(row['points'], policy=policy) != row['performance']:
            raise ValueError('price_replay_mismatch:' + row['id'])
    observed = [row for row in series if row['performance']['market']]
    counts = {
        'series_count': len(series),
        'price_series_with_two_quotes': len(observed),
        'observed_2x': sum(row['performance']['market']['milestones']['2'] is not None for row in observed),
        'final_2x': sum(row['performance']['market']['final_multiple'] >= 2 for row in observed),
    }
    if any(summary[name] != count for name, count in counts.items()):
        raise ValueError('casebook_summary_mismatch')
    actions = dict(Counter(e['action'] for row in observed for e in row['performance']['scenario']['events']))
    if actions != summary['scenario_events']:
        raise ValueError('casebook_action_count_mismatch')
    if 'unique_tokens' in summary:
        groups = token_groups(series)
        if summary['unique_tokens'] != len(groups):
            raise ValueError('casebook_token_count_mismatch')
        expected = {'README.md'} | {group['id'] + '.md' for group in groups}
        actual = {path.name for path in (directory / 'tokens').glob('*.md')}
        if actual != expected:
            raise ValueError('casebook_token_coverage_mismatch')
    return {'schema': SCHEMA, 'files_verified': len(manifest['files']), 'observations': len(observations),
            'native_calls': len(calls), 'series_recomputed': len(series), 'decision_events': sum(actions.values())}


def publish(capture: Path, report_path: Path, output: Path):
    """Export source-bound observations and a frozen report to a new directory."""
    if output.exists():
        raise FileExistsError(output)
    report = _read(report_path)
    _validate_series(report['rows'])
    manifest = _read(capture / 'manifest.json')
    freeze = _read(capture / 'sample-freeze.json')
    if _hash(capture / 'sample.json') != freeze['sample_sha256']:
        raise ValueError('sample_freeze_hash_mismatch')
    for name, expected in report['input_sha256'].items():
        if Path(name).name != name or _hash(capture / name) != expected:
            raise ValueError('report_input_hash_mismatch')
    receipts = manifest['captures']
    _index(receipts, 'capture_id')
    for receipt in receipts:
        identifier = receipt['capture_id']
        if Path(identifier).name != identifier or '/' in identifier or '\\' in identifier:
            raise ValueError('unsafe_capture_id')
        if _hash(capture / 'raw' / (identifier + '.json')) != receipt['raw_sha256']:
            raise ValueError('capture_hash_mismatch')
    samples = _read(capture / 'sample.json')
    decisions = _lines(capture / 'task-results.jsonl')
    calls = _lines(capture / 'task-model-calls.jsonl')
    _verify_parameter_sources(capture, samples, receipts)
    _verify_report_sources(capture, manifest, samples, report)
    validate_native_records(samples, decisions, calls)
    # Namespace projection follows original-byte validation. Archived inputs are never rewritten.
    samples = deepcopy(samples)
    for entry in samples:
        entry['archived_event_sha256'] = digest(entry['event'])
        entry['event']['source'] = 'omnia.market.rank'
        entry['projection'] = 'omnia.public-source.v1'
    native = _index(decisions, 'observation_id')
    summary = dict(report['summary'])
    summary['native_task_metrics'] = _metrics(decisions)
    summary['capture_count'] = len(receipts)
    summary['observation_count'] = len(samples)
    summary['native_call_count'] = len(calls)
    summary['source_parameter_values'] = sum(len(entry['event']['fields']) for entry in samples)
    summary['unique_tokens'] = len(token_groups(report['rows']))
    summary['observations_by_chain'] = dict(Counter(entry['event']['identity']['chain'] for entry in samples))
    summary['captures_by_chain'] = dict(Counter('solana' if row['chain'] == 'sol' else row['chain'] for row in receipts))
    summary['model_evaluation_scope'] = 'Three native tasks per observation; full strategy and account execution were not run.'
    summary['price_basis'] = 'First captured quote of each series; peak and last observed quote within this window.'
    output.mkdir(parents=True)
    (output / 'cases').mkdir()
    _jsonl(output / 'observations.jsonl', samples)
    _jsonl(output / 'native-decisions.jsonl', decisions)
    _jsonl(output / 'native-calls.jsonl', calls)
    _jsonl(output / 'series.jsonl', report['rows'])
    for chain in ('robinhood', 'bsc', 'solana'):
        folder = output / 'series' / chain
        folder.mkdir(parents=True)
        table = [f'# {chain.upper()} results', '', '[Window overview](../../README.md)', '',
                 '| Token | Contract | Quotes | Peak | Final | Record |', '| --- | --- | ---: | ---: | ---: | --- |']
        for row in report['rows']:
            if row['identity']['chain'] != chain:
                continue
            _json(folder / (row['id'] + '.json'), row)
            market = row['performance']['market']
            peak = f"{market['peak_multiple']:.3f}x" if market else '—'
            final = f"{market['final_multiple']:.3f}x" if market else '—'
            table.append(f"| {_md(row['name'])} | `{row['identity']['contract']}` | {len(row['points'])} | {peak} | {final} | [Inspect]({row['id']}.json) |")
        (folder / 'README.md').write_text('\n'.join(table) + '\n', encoding='utf-8', newline='\n')
    _jsonl(output / 'capture-receipts.jsonl', [
        {key: row[key] for key in ('capture_id', 'received_at', 'chain', 'endpoint', 'raw_sha256')}
        for row in receipts])
    _json(output / 'summary.json', summary)
    _json(output / 'sample-freeze.json', freeze)
    parameter_rows, case_links = [], []
    for entry in samples:
        event = entry['event']
        case_id = digest(event['id'])[:16]
        case_links.append((entry, case_id))
        matching = [row['id'] for row in report['rows'] if row['identity'] == event['identity']]
        packet = {'observation': entry, 'native_decision': native[event['id']],
                  'native_calls': [row for row in calls if row['observation_id'] == event['id']],
                  'price_series_ids': matching, 'observation_sha256': digest(event)}
        _json(output / 'cases' / (case_id + '.json'), packet)
        lines = [f"# {_md(entry['name'])}", '', f"**{event['identity']['chain']}** · `{event['identity']['contract']}`", '',
                 f"Observed: {event['observed_at']}", '', f"[Complete record]({case_id}.json) · [Window overview](../README.md)", '',
                 '## Native JEV/LAYA assessments', '', '| Task | Answer | Probability | Gate | Reference label |',
                 '| --- | --- | ---: | --- | --- |']
        for task, check in native[event['id']]['task_checks'].items():
            answer = check['answers'][task]
            lines.append(f"| {task} | {answer['choice']} | {answer['answer_probability']:.4f} | {check['status']} | {native[event['id']]['expected'][task]} |")
        lines += ['', '## Source parameters', '', 'Values retain their original units; null means not reported.', '',
                  '| Parameter | Value | Unit | Window (seconds) |', '| --- | --- | --- | ---: |']
        for key, field in event['fields'].items():
            lines.append(f"| `{key}` | {_md(json.dumps(field['value'], ensure_ascii=False))} | {_md(field['unit'])} | {field['window_seconds']} |")
            parameter_rows.append({'observation_id': event['id'], **event['identity'], 'parameter': key, **field})
        lines += ['', '## Provenance', '', f"- Observation hash: `{digest(event)}`",
                  f"- Source capture hash: `{entry['raw_hash']}`",
                  '- Every field timestamp, evidence reference and source mapping is included in the complete record.',
                  '- Reference labels follow task rules. Model answers and acceptance gates are retained unchanged.', '']
        (output / 'cases' / (case_id + '.md')).write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    _csv(output / 'parameters.csv', ['observation_id', 'chain', 'network_id', 'contract', 'pool', 'parameter',
                                   'value', 'unit', 'window_seconds', 'observed_at', 'evidence'], parameter_rows)
    _csv(output / 'assessments.csv', ['observation_id', 'chain', 'contract', 'task', 'choice', 'probability',
                                    'status', 'reference', 'agreement', 'model_revision', 'processed_at', 'evidence'],
         ({'observation_id': row['observation_id'], **row['identity'], 'task': task,
           'choice': check['answers'][task]['choice'], 'probability': check['answers'][task]['answer_probability'],
           'status': check['status'], 'reference': row['expected'][task],
           'agreement': check['answers'][task]['choice'] == row['expected'][task],
           'model_revision': check['engine']['configuration']['revision'],
           'processed_at': check['processed_at'], 'evidence': check['evidence']}
          for row in decisions for task, check in row['task_checks'].items()))
    _csv(output / 'prechecks.csv', ['observation_id', 'chain', 'contract', 'at', 'gate', 'reasons',
                                  'risk_reasons', 'full_strategy_executed'],
         ({**row['identity'], **evaluation} for row in report['rows'] for evaluation in row['evaluations']))
    _csv(output / 'decisions.csv', ['series_id', 'chain', 'contract', 'pool', 'origin', 'at', 'action', 'price',
                                  'quantity', 'sold_quantity', 'remaining_quantity', 'realized_profit_usd', 'reason', 'evidence'],
         ({'series_id': row['id'], **row['identity'], 'origin': 'quote_exit_policy', **event}
          for row in report['rows'] for event in (row['performance'].get('scenario') or {}).get('events', [])))
    _csv(output / 'series.csv', ['series_id', 'name', 'chain', 'network_id', 'contract', 'pool', 'quote_count',
                               'first_price_usd', 'peak_price_usd', 'last_price_usd', 'peak_multiple', 'final_multiple',
                               'first_at', 'last_at', 'final_action', 'gross_profit_usd'],
         ({'series_id': row['id'], 'name': row['name'], **row['identity'], **row['performance'],
           **(row['performance']['market'] or {}), **(row['performance']['scenario'] or {})} for row in report['rows']))
    write_tokens(output, report['rows'], samples)
    _write_overview(output, summary, report['rows'], case_links)
    files = {path.relative_to(output).as_posix(): _hash(path) for path in sorted(output.rglob('*')) if path.is_file()}
    _json(output / 'manifest.json', {'schema': SCHEMA, 'files': files,
          'source_report_sha256': _hash(report_path), 'source_input_sha256': report['input_sha256'],
          'source_implementation_sha256': report['implementation_sha256'],
          'export': 'Complete frozen cohort and all report series; no outcome-based exclusion.',
          'raw_archive': 'Capture receipts preserve hashes; full provider payloads and local databases are not distributed.'})
    return verify(output)


def refresh_views(directory):
    """Regenerate presentation from verified frozen records without changing native evidence."""
    verify(directory)
    rows = _lines(directory / 'series.jsonl')
    samples = _lines(directory / 'observations.jsonl')
    summary = _read(directory / 'summary.json')
    summary['unique_tokens'] = len(token_groups(rows))
    _json(directory / 'summary.json', summary)
    write_tokens(directory, rows, samples)
    _write_overview(directory, summary, rows, [(entry, digest(entry['event']['id'])[:16]) for entry in samples])
    manifest = _read(directory / 'manifest.json')
    manifest['presentation'] = {'version': 'omnia.trading.casebook-views.v2',
                                'implementation_sha256': _hash(Path(__file__).with_name('casebook_views.py'))}
    manifest['files'] = {path.relative_to(directory).as_posix(): _hash(path)
                         for path in sorted(directory.rglob('*')) if path.is_file() and path != directory / 'manifest.json'}
    _json(directory / 'manifest.json', manifest)
    return verify(directory)


def _write_overview(output, summary, rows, cases):
    observed = [row for row in rows if row['performance']['market']]
    tokens = token_groups(rows)
    start, end = timestamp(summary['capture_start']), timestamp(summary['capture_end'])
    period = f"**{start:%Y-%m-%d %H:%M:%S} to {end:%Y-%m-%d %H:%M:%S} UTC**"
    lines = ['# Market window', '', period, '',
             'Robinhood Chain · BSC · Solana', '',
             '| Captures | Unique tokens | Series | Two or more quotes | Single or no quote |',
             '| ---: | ---: | ---: | ---: | ---: |',
             f"| {summary['capture_count']} | {len(tokens)} | {len(rows)} | {len(observed)} | {len(rows) - len(observed)} |", '',
             '## All tokens and curves', '',
             '[Open the complete token index](tokens/README.md). Each network and contract appears once, with every pool series, quote, native assessment and policy event linked from its record.', '',
             'Curves include every recorded price, including declines. Multiples start at the first quote; peak is the highest quote in this window, not an all-time high.', '',
             '| Series ending above entry | Below entry | Unchanged |', '| ---: | ---: | ---: |',
             f"| {sum(r['performance']['market']['final_multiple'] > 1 for r in observed)} | "
             f"{sum(r['performance']['market']['final_multiple'] < 1 for r in observed)} | "
             f"{sum(r['performance']['market']['final_multiple'] == 1 for r in observed)} |"]
    lines += ['', '**Complete coverage:** [all series](series.csv), [every quote and milestone](series.jsonl), [exit-policy timeline](decisions.csv).', '',
              '**Browse by network:** [Robinhood](series/robinhood/README.md) · [BSC](series/bsc/README.md) · [Solana](series/solana/README.md). Every series has its own full record.', '',
              'The exit-policy timeline applies an independent USD 100 entry at the first quote. It records partial exits and TP/SL at captured prices. Costs are excluded; these calculations are separate from native model decisions.', '',
              '## JEV/LAYA assessments', '',
              f"{summary['observation_count']} observations · {summary['native_call_count']} native responses · {summary['source_parameter_values']} source parameter values. See the selection record for the frozen cohort and its timestamp.", '',
              '| Task | Responses | Agreement with reference rule | Accepted | Accepted disagreements |',
              '| --- | ---: | ---: | ---: | ---: |']
    for task, metric in summary['native_task_metrics'].items():
        lines.append(f"| {task} | {metric['answered']} | {metric['agreement']}/{metric['answered']} | {metric['accepted']} | {metric['accepted_wrong']} |")
    lines += ['', 'Reference labels are deterministic task rules. Records retain every agreement and disagreement. The current engine checks task coverage before requesting a risk answer; historical responses are preserved unchanged.', '',
              '[Native response table](assessments.csv) · [Full native records](native-decisions.jsonl) · [Exact model inputs and outputs](native-calls.jsonl) · [All source parameters](parameters.csv) · [Entry prechecks](prechecks.csv)', '',
              '## Contract records', '', '| Token | Network | Contract | Parameters | Record |', '| --- | --- | --- | ---: | --- |']
    for entry, case_id in cases:
        event = entry['event']
        lines.append(f"| {_md(entry['name'])} | {event['identity']['chain']} | `{event['identity']['contract']}` | {len(event['fields'])} | [Inspect](cases/{case_id}.md) |")
    lines += ['', '## Reproduce', '', '```bash', 'python -m pip install -e .',
              'omnia-trading-casebook verify examples/market-window-2026-09-28', '```', '',
              'Verification checks published file hashes, binds native inputs to observation fields, compares stored answers, and recalculates every price trajectory and exit-policy event. It makes no network or model calls.', '',
              '[Manifest](manifest.json) · [Summary](summary.json) · [Capture receipts](capture-receipts.jsonl) · [Selection record](sample-freeze.json)', '']
    (output / 'README.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('verify', help='Verify a published window without inference')
    inspect.add_argument('directory', type=Path)
    refresh = commands.add_parser('refresh-views', help='Refresh Markdown and curves from verified records')
    refresh.add_argument('directory', type=Path)
    export = commands.add_parser('export', help='Export an intact capture and its frozen report')
    export.add_argument('--capture-dir', type=Path, required=True)
    export.add_argument('--report', type=Path, required=True)
    export.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        result = verify(args.directory)
    elif args.command == 'refresh-views':
        result = refresh_views(args.directory)
    else:
        result = publish(args.capture_dir, args.report, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
