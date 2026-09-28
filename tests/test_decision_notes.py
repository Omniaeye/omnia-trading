# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
from datetime import datetime
import unittest
from omnia_trading.decision_notes import explain_observation


class DecisionNotesTests(unittest.TestCase):
    def setUp(self):
        self.event = json.loads((Path(__file__).resolve().parents[1] / 'examples/strategy.jsonl').read_bytes())['observation']
        self.now = datetime.fromisoformat(self.event['observed_at'].replace('Z', '+00:00'))

    def notes(self, **kwargs):
        return explain_observation(self.event, now=self.now, **kwargs)['notes']

    def test_supportive_does_not_imply_entry(self):
        self.event['fields']['buys']['value'] = 55
        self.event['fields']['sells']['value'] = 45
        codes = {note['code'] for note in self.notes()}
        self.assertIn('FLOW_BUY_DOMINANT', codes)
        self.assertIn('ENTRY_BUY_SHARE_BELOW_MIN', codes)

    def test_zero_activity_is_different_from_balanced_activity(self):
        for count, expected in [(0, 'FLOW_NO_ACTIVITY'), (10, 'FLOW_BALANCED')]:
            for key in ('buys', 'sells'):
                self.event['fields'][key]['value'] = count
            self.assertIn(expected, {note['code'] for note in self.notes()})

    def test_missing_risk_is_not_reported_clear(self):
        del self.event['fields']['sell_simulation_success']
        codes = {note['code'] for note in self.notes()}
        self.assertIn('RISK_EVIDENCE_INCOMPLETE', codes)
        self.assertNotIn('RISK_REPORTS_CLEAR', codes)

    def test_model_disagreement_retains_native_answer(self):
        record = {'flow': {'status': 'accepted', 'answers': {'flow': {'choice': 'weak', 'answer_probability': .99}}}}
        notes = self.notes(native_checks=record)
        comparison = next(note for note in notes if note['code'] == 'MODEL_RULE_DISAGREEMENT')
        self.assertEqual(comparison['origin'], 'comparison')
        self.assertEqual(comparison['values']['model_choice'], 'weak')
        self.assertEqual(record['flow']['answers']['flow']['choice'], 'weak')

    def test_unknown_scale_does_not_trigger_numeric_limit(self):
        self.event['fields']['liquidity']['unit'] = 'source_scale'
        codes = {note['code'] for note in self.notes()}
        self.assertIn('LIQUIDITY_USD_UNVERIFIED', codes)
        self.assertNotIn('LIQUIDITY_MIN_MET', codes)


if __name__ == '__main__':
    unittest.main()
