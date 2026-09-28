# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
import contextlib
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
from omnia_trading import reporting as builder
from omnia_trading.casebook import _verify_report_sources


class PerformanceReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source'
        (self.source / 'raw').mkdir(parents=True)
        self.output = Path(self.temp.name) / 'report'
        self.event = json.loads((ROOT / 'examples/strategy.jsonl').read_bytes())['observation']
        at = datetime.fromisoformat(self.event['observed_at'].replace('Z', '+00:00')).isoformat()
        raw = b'{"code":0,"data":{"rank":[]}}'
        (self.source / 'raw/capture.json').write_bytes(raw)
        manifest = {'started_at': at, 'ended_at': at, 'duration_seconds': 900,
                    'captures': [{'capture_id': 'capture', 'received_at': at,
                                  'endpoint': 'market_rank', 'chain': self.event['identity']['chain'],
                                  'raw_sha256': hashlib.sha256(raw).hexdigest()}]}
        (self.source / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        (self.source / 'sample.json').write_text(json.dumps([
            {'event': self.event, 'name': 'Example', 'endpoint': 'market_rank'}]), encoding='utf-8')
        self.native = {'observation_id': self.event['id'], 'identity': self.event['identity'], 'task_checks': {}}
        self.write_native()

    def write_native(self):
        (self.source / 'task-results.jsonl').write_text(json.dumps(self.native) + '\n', encoding='utf-8')

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            builder.build(self.source, self.output)

    def test_report_preserves_notes_and_unknown_performance(self):
        self.build()
        report = json.loads((self.output / 'report.json').read_bytes())
        self.assertEqual(report['summary']['capture_duration_seconds'], 900)
        row = report['rows'][0]
        self.assertIsNone(row['performance']['market'])
        self.assertEqual(row['evaluations'][0]['decision_notes']['observation_id'], self.event['id'])
        self.assertFalse(report['publication_authorized'])
        self.assertEqual({path.name for path in self.output.iterdir()}, {'report.json'})

    def test_tampered_capture_cannot_produce_a_report(self):
        (self.source / 'raw/capture.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'capture_hash_mismatch'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_frozen_sample_cannot_be_replaced(self):
        (self.source / 'sample-freeze.json').write_text(json.dumps({'sample_sha256': '0' * 64}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'sample_freeze_hash_mismatch'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_duplicate_sample_is_rejected(self):
        path = self.source / 'sample.json'
        sample = json.loads(path.read_bytes())
        path.write_text(json.dumps(sample + sample), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate_sample_observation'):
            self.build()

    def test_recomputed_report_cannot_invent_source_quotes(self):
        self.build()
        report = json.loads((self.output / 'report.json').read_bytes())
        report['rows'][0]['points'] = [{'at': self.event['observed_at'], 'price': 999.0}]
        manifest = json.loads((self.source / 'manifest.json').read_bytes())
        sample = json.loads((self.source / 'sample.json').read_bytes())
        with self.assertRaisesRegex(ValueError, 'report_quote_source_mismatch'):
            _verify_report_sources(self.source, manifest, sample, report)

    def test_native_answer_from_another_identity_is_rejected(self):
        self.native['identity'] = {**self.native['identity'], 'network_id': 'another.network'}
        self.write_native()
        with self.assertRaisesRegex(ValueError, 'native_identity_mismatch'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_duplicate_native_record_is_rejected(self):
        with (self.source / 'task-results.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(self.native) + '\n')
        with self.assertRaisesRegex(ValueError, 'duplicate_native_observation'):
            self.build()


if __name__ == '__main__':
    unittest.main()
