# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Recovery boundaries exercise independent SQLite connections."""
import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from test_ledger import request, prediction
from omnia_trading._engine.ledger import DecisionLedger, DecisionError


class RecoveryTests(unittest.TestCase):
    def test_cached_read_remains_available_during_other_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audit.db'
            ledger = DecisionLedger(path)
            manifest = {'revision': 'r1'}
            ledger.decide(request(), prediction, manifest=manifest)
            entered, release = threading.Event(), threading.Event()
            errors = []

            def worker():
                other = DecisionLedger(path)
                row = request()
                row['id'] = 'different-request'

                def slow(*args):
                    entered.set()
                    if not release.wait(3):
                        raise TimeoutError('test barrier')
                    return prediction(*args)

                try:
                    other.decide(row, slow, manifest=manifest)
                except Exception as error:
                    errors.append(error)
                finally:
                    other.close()

            thread = threading.Thread(target=worker)
            thread.start()
            try:
                self.assertTrue(entered.wait(3))
                ledger.db.execute('PRAGMA busy_timeout=20')
                self.assertTrue(ledger.decide(request(), prediction, manifest=manifest)['cache_hit'])
            finally:
                release.set()
                thread.join(3)
                ledger.close()
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])

    def test_expired_owner_cannot_commit_and_replay_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = DecisionLedger(Path(folder) / 'audit.db')

            def expire(*args):
                ledger.db.execute('UPDATE claims SET expires=?', (time.time() - 1,))
                return prediction(*args)

            try:
                with self.assertRaises(DecisionError):
                    ledger.decide(request(), expire, manifest={'revision': 'r1'})
                self.assertEqual(ledger.db.execute('SELECT count(*) FROM decisions').fetchone()[0], 0)
                self.assertEqual(ledger.db.execute('SELECT count(*) FROM claims').fetchone()[0], 0)
                self.assertEqual(ledger.decide(request(), prediction, manifest={'revision': 'r1'})['status'], 'accepted')
            finally:
                ledger.close()

    def test_assessment_is_persisted_without_mutating_caller(self):
        ledger = DecisionLedger(':memory:')
        try:
            result = {'schema': 'omnia.result.v1', 'status': 'skip', 'policy': {'version': 1}}
            before = copy.deepcopy(result)
            saved = ledger.record_assessment(result)
            self.assertEqual(result, before)
            self.assertEqual(ledger.get_assessment(saved['assessment_id']), saved)
            self.assertEqual(ledger.record_assessment(result), saved)
            self.assertEqual(ledger.db.execute('SELECT count(*) FROM assessments').fetchone()[0], 1)
        finally:
            ledger.close()

    def test_failed_provider_releases_claim_and_keeps_private_error_out(self):
        ledger = DecisionLedger(':memory:')
        try:
            def failure(*_):
                raise RuntimeError('credential-not-for-storage')
            with self.assertRaises(DecisionError):
                ledger.decide(request(), failure, manifest={'revision': 'r1'})
            self.assertEqual(ledger.db.execute('SELECT count(*) FROM claims').fetchone()[0], 0)
            self.assertEqual(ledger.db.execute('SELECT kind FROM failures').fetchone()[0], 'RuntimeError')
        finally:
            ledger.close()

    def test_full_length_source_urls_reach_evidence_contract(self):
        ledger = DecisionLedger(':memory:')
        try:
            row = request()
            row['evidence'] = ['https://example.com/' + 'x' * 2000]
            self.assertEqual(ledger.decide(row, prediction, manifest={'revision': 'r1'})['status'], 'accepted')
        finally:
            ledger.close()
