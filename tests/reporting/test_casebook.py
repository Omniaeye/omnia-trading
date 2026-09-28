# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Published captures are regression data, with no model or network dependency."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from omnia_trading.casebook import _csv, _validate_series, _verify_parameter_sources, validate_native_records, verify

WINDOW = Path(__file__).resolve().parents[2] / 'examples/market-window-2026-09-28'


class CasebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = [json.loads(line) for line in (WINDOW / 'observations.jsonl').read_text().splitlines()]
        cls.decisions = [json.loads(line) for line in (WINDOW / 'native-decisions.jsonl').read_text().splitlines()]
        cls.calls = [json.loads(line) for line in (WINDOW / 'native-calls.jsonl').read_text().splitlines()]

    def test_complete_published_window_replays_without_inference(self):
        receipt = verify(WINDOW)
        self.assertEqual(receipt['observations'], 60)
        self.assertEqual(receipt['native_calls'], 180)
        self.assertEqual(receipt['series_recomputed'], 621)
        self.assertEqual(receipt['decision_events'], 14077)

    def test_changed_observation_cannot_reuse_a_native_answer(self):
        samples = deepcopy(self.samples)
        samples[0]['event']['fields']['buys']['value'] += 1
        with self.assertRaisesRegex(ValueError, 'native_field_mismatch'):
            validate_native_records(samples, self.decisions, self.calls)

    def test_changed_prompt_cannot_reuse_a_native_answer(self):
        calls = deepcopy(self.calls)
        calls[0]['questions']['risk']['instructions'] += ' altered'
        with self.assertRaisesRegex(ValueError, 'native_question_hash_mismatch'):
            validate_native_records(self.samples, self.decisions, calls)

    def test_missing_or_duplicate_native_calls_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'native_call_missing'):
            validate_native_records(self.samples, self.decisions, self.calls[1:])
        with self.assertRaisesRegex(ValueError, 'duplicate_native_call'):
            validate_native_records(self.samples, self.decisions, self.calls + self.calls[:1])

    def test_changed_answer_cannot_match_a_native_receipt(self):
        calls = deepcopy(self.calls)
        calls[0]['response']['answers']['risk']['choice'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'native_answer_mismatch'):
            validate_native_records(self.samples, self.decisions, calls)

    def test_acceptance_cannot_be_changed_without_the_native_probability(self):
        decisions = deepcopy(self.decisions)
        decisions[0]['task_checks']['flow']['status'] = 'accepted'
        decisions[0]['task_checks']['flow']['answers']['flow']['answer_probability'] = 1.0
        with self.assertRaisesRegex(ValueError, 'native_acceptance_mismatch'):
            validate_native_records(self.samples, decisions, self.calls)

    def test_duplicate_observations_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate_sample_observation'):
            validate_native_records(self.samples + self.samples[:1], self.decisions, self.calls)

    def test_series_ids_cannot_escape_export_directory(self):
        for identifier in ('../outside', '/tmp/outside', 'C:/outside', 'bad/name'):
            with self.subTest(identifier=identifier), self.assertRaisesRegex(ValueError, 'invalid_series_id'):
                _validate_series([{'id': identifier}])

    def test_manifest_rejects_escape_and_modified_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = {'schema': 'omnia.trading.casebook.v1', 'files': {'../outside.json': '0' * 64}}
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'unsafe_casebook_path'):
                verify(root)
            (root / 'summary.json').write_text('{}')
            manifest['files'] = {'summary.json': hashlib.sha256(b'original').hexdigest()}
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'casebook_hash_mismatch'):
                verify(root)

    def test_csv_source_text_cannot_execute_a_spreadsheet_formula(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'export.csv'
            _csv(path, ['value'], [{'value': '=1+1'}, {'value': '@command'}, {'value': -12.5}])
            self.assertEqual(path.read_text().splitlines(), ['value', "'=1+1", "'@command", '-12.5'])

    def test_public_source_namespace_preserves_archived_fingerprint(self):
        for row in self.samples:
            self.assertEqual(row['event']['source'], 'omnia.market.rank')
            self.assertEqual(row['projection'], 'omnia.public-source.v1')
            self.assertRegex(row['archived_event_sha256'], r'^[a-f0-9]{64}$')

    def test_integer_flag_conversion_requires_explicit_source_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'raw').mkdir()
            raw = b'{"flag":0}'
            (root / 'raw/capture.json').write_bytes(raw)
            raw_hash = hashlib.sha256(raw).hexdigest()
            observed = '2026-09-28T00:00:00Z'
            samples = [{'raw_hash': raw_hash, 'event': {'id': 'capture:token', 'observed_at': observed,
                        'fields': {'is_renounced': {'value': False, 'unit': 'boolean'}}},
                        'mappings': {'is_renounced': {'path': '/flag', 'source_value': 0}}}]
            receipts = [{'capture_id': 'capture', 'raw_sha256': raw_hash, 'received_at': observed}]
            with self.assertRaisesRegex(ValueError, 'parameter_source_value_mismatch'):
                _verify_parameter_sources(root, samples, receipts)
            samples[0]['mappings']['is_renounced'].update({
                'transform': 'explicit_source_contract', 'source_contract_verified': True,
                'contract_reason': 'provider_integer_flag_not_independent_security_verdict'})
            _verify_parameter_sources(root, samples, receipts)


if __name__ == '__main__':
    unittest.main()
