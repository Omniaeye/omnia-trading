# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
from tests.helpers import Backend, datapoint, event
from omnia_trading.pipeline import process
from omnia_trading._engine.ledger import DecisionLedger


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.ledger = DecisionLedger(Path(self.folder.name) / 'decisions.db')

    def tearDown(self):
        self.ledger.close()
        self.folder.cleanup()

    def test_every_populated_group_is_assessed_and_cached(self):
        item = event()
        item['fields']['holder_count'] = datapoint(200, 'count')
        backend = Backend()
        first = process(item, self.ledger, backend)
        second = process(item, self.ledger, backend)
        self.assertEqual(first['disposition'], 'candidate')
        self.assertEqual(first['parameter_count'], 4)
        self.assertEqual(set(first['groups']), {'Market', 'Risk', 'Holders'})
        self.assertEqual(backend.calls, 3)
        self.assertTrue(all(x['cache_hit'] for x in second['groups'].values()))
        self.assertFalse(first['execution_authorized'])

    def test_skip_never_loads_model(self):
        item = event()
        item['fields']['is_honeypot']['value'] = True
        backend = Backend()
        self.assertEqual(process(item, self.ledger, backend)['disposition'], 'skip')
        self.assertEqual(backend.calls, 0)

    def test_maximum_source_id_still_has_valid_group_ids(self):
        item = event()
        item['id'] = 'a' * 200
        result = process(item, self.ledger, Backend())
        self.assertEqual(result['disposition'], 'candidate')
        self.assertEqual(result['observation_id'], item['id'])
        self.assertEqual(result['group_failures'], {})

    def test_insufficient_is_never_candidate(self):
        self.assertEqual(process(event(), self.ledger, Backend('insufficient'))['disposition'], 'review')

    def test_model_failure_is_explicit(self):
        backend = Backend('invalid')
        result = process(event(), self.ledger, backend)
        self.assertEqual(result['disposition'], 'review')
        self.assertEqual(set(result['group_failures']), {'Market', 'Risk'})

    def test_source_unit_change_invalidates_record(self):
        item = event()
        backend = Backend()
        first = process(item, self.ledger, backend)
        item['fields']['market_cap']['unit'] = 'native'
        second = process(item, self.ledger, backend)
        self.assertNotEqual(first['observation_hash'], second['observation_hash'])
        self.assertEqual(second['disposition'], 'review')

    def test_unavailable_fields_remain_accounted_for_without_inference(self):
        item = event()
        item['fields']['holder_count'] = datapoint(None, 'count')
        item['fields']['slot'] = datapoint(42, 'count')
        result = process(item, self.ledger, Backend())
        self.assertEqual(result['disposition'], 'candidate')
        self.assertEqual(result['unavailable_fields'], {'holder_count': 'not_reported', 'slot': 'not_applicable'})
        assessed = {key for batch in result['assessment_batches'].values() for key in batch['fields']}
        self.assertEqual(assessed | set(result['unavailable_fields']), set(item['fields']))

    def test_all_null_fields_cannot_be_a_candidate(self):
        item = event()
        for field in item['fields'].values():
            field['value'] = None
        backend = Backend()
        result = process(item, self.ledger, backend)
        self.assertEqual(result['disposition'], 'review')
        self.assertIn('no_reported_fields', result['reasons'])
        self.assertEqual(backend.calls, 0)
