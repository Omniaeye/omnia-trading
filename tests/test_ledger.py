# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
import copy
import json
import sys
import tempfile
import unittest
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omnia_trading._engine.ledger import DecisionError, DecisionLedger, validate_answers, validate_request


def request():
    return {"id": "event-A", "state": "Fix retry after timeout", "evidence": ["repo/commit/abc"],
            "questions": {"route": {"type": "choice", "instructions": "Which route?",
                                      "criteria": {"keep": "Useful change", "review": "Needs context"}}}}


def prediction(state, questions):
    return {"answers": {"route": {"type": "choice", "choice": "keep",
                                  "probabilities": {"keep": .9, "review": .1}, "confidence": .53}}}


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "ledger.sqlite3"
        self.ledger = DecisionLedger(self.path)
        self.manifest = {"revision": "a" * 40, "model": "english", "max_len": 512}

    def tearDown(self):
        self.ledger.close()
        self.folder.cleanup()

    def decide(self, value=None, predictor=prediction, **kwargs):
        return self.ledger.decide(value or request(), predictor, manifest=self.manifest, **kwargs)

    def test_probability_not_entropy_drives_policy(self):
        result = self.decide()
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["answers"]["route"]["model_confidence"], .53)

    def test_review_boundary(self):
        self.assertEqual(self.decide(min_probability=.91)["status"], "review")
        self.assertEqual(self.decide(min_probability=.9)["status"], "accepted")

    def test_replay_never_calls_provider_again(self):
        first = self.decide()
        result = self.decide(predictor=lambda *_: self.fail("duplicate inference"))
        self.assertTrue(result["cache_hit"])
        self.assertEqual(result["decision_id"], first["decision_id"])

    def test_cache_survives_reopen(self):
        self.decide()
        self.ledger.close()
        self.ledger = DecisionLedger(self.path)
        self.assertTrue(self.decide(predictor=lambda *_: self.fail("duplicate"))["cache_hit"])

    def test_changed_content_identity_policy_and_manifest_invalidate_cache(self):
        initial = self.decide()["decision_id"]
        for field, value in (("state", "fix retry after timeout"), ("id", "event-a"), ("evidence", ["different"])):
            row = request()
            row[field] = value
            self.assertNotEqual(initial, self.decide(row)["decision_id"])
        self.assertNotEqual(initial, self.decide(min_probability=.91)["decision_id"])
        self.manifest["revision"] = "b" * 40
        self.assertNotEqual(initial, self.decide()["decision_id"])

    def test_option_order_invalidates_cache(self):
        initial = self.decide()["decision_id"]
        row = request()
        row["questions"]["route"]["criteria"] = {"review": "Needs context", "keep": "Useful change"}
        self.assertNotEqual(initial, self.decide(row)["decision_id"])

    def test_state_json_order_is_part_of_model_input(self):
        first, second = request(), request()
        first["state"] = {"primary": "one", "quote": "two"}
        second["state"] = {"quote": "two", "primary": "one"}
        self.assertNotEqual(self.decide(first)["decision_id"], self.decide(second)["decision_id"])

    def test_two_connections_share_one_inference(self):
        calls, results, errors = [], [], []
        def provider(*args):
            calls.append(1)
            time.sleep(.03)
            return prediction(*args)
        def worker():
            ledger = DecisionLedger(self.path)
            try:
                results.append(ledger.decide(request(), provider, manifest=self.manifest))
            except Exception as error:
                errors.append(error)
            finally:
                ledger.close()
        workers = [threading.Thread(target=worker) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(sorted(row["cache_hit"] for row in results), [False, True])

    def test_no_input_text_or_raw_error_in_ledger(self):
        row = request()
        row["state"] = "private-body-do-not-store"
        result = self.decide(row)
        self.assertNotIn(row["state"], json.dumps(result))
        self.assertNotIn(row["state"], self.ledger.db.execute("SELECT record FROM decisions").fetchone()[0])

    def test_failure_is_recorded_and_retry_is_possible(self):
        def broken(*_):
            raise RuntimeError("secret-password-do-not-log")
        with self.assertRaises(DecisionError) as error:
            self.decide(predictor=broken)
        self.assertNotIn("secret-password", str(error.exception))
        self.assertEqual(self.ledger.db.execute("SELECT kind FROM failures").fetchone()[0], "RuntimeError")
        self.assertFalse(self.decide()["cache_hit"])

    def test_malformed_output_is_not_cached(self):
        with self.assertRaises(DecisionError):
            self.decide(predictor=lambda *_: {"answers": {}})
        self.assertEqual(self.ledger.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_no_extra_output_can_leak_provider_state(self):
        raw = prediction(None, None)
        raw["private"] = "not-for-export"
        result = self.decide(predictor=lambda *_: raw)
        self.assertNotIn("not-for-export", json.dumps(result))

    def test_provider_cannot_mutate_the_audit_input(self):
        row = request()
        row["state"] = {"body": "keep original"}
        def mutate(state, questions):
            state["body"] = "changed"
            questions["route"]["instructions"] = "changed"
            return prediction(None, None)
        result = self.decide(row, predictor=mutate)
        self.assertEqual(row["state"]["body"], "keep original")
        self.assertEqual(result["input_sha256"], self.decide(row)["input_sha256"])

    def test_request_rejections(self):
        for mutation in (lambda r: r.update(extra=True), lambda r: r.update(state=""),
                         lambda r: r.update(evidence=[]), lambda r: r.update(state={"n": float("nan")}),
                         lambda r: r["questions"]["route"].update(type="unsupported")):
            row = request()
            mutation(row)
            with self.assertRaises(ValueError):
                validate_request(row)
        with self.assertRaises(ValueError):
            validate_request(request(), max_bytes=10)

    def test_unicode_is_preserved(self):
        row = request()
        row["state"] = "修复重试逻辑 — correção"
        self.assertEqual(self.decide(row)["status"], "accepted")

    def test_invalid_probabilities_are_rejected(self):
        for value in (True, float("inf"), float("nan"), -1, 1.2, "0.9"):
            raw = prediction(None, None)
            raw["answers"]["route"]["probabilities"]["keep"] = value
            with self.assertRaises(ValueError):
                validate_answers(raw, request()["questions"])

    def test_distribution_and_choice_must_agree(self):
        for key, value in (("choice", "unknown"), ("choice", "review"), ("answer_confidence", .1)):
            raw = prediction(None, None)
            raw["answers"]["route"][key] = value
            with self.assertRaises(ValueError):
                validate_answers(raw, request()["questions"])
        raw = prediction(None, None)
        raw["answers"]["route"]["probabilities"]["review"] = .9
        with self.assertRaises(ValueError):
            validate_answers(raw, request()["questions"])

    def test_score_and_binary_answers(self):
        questions = {"amount": {"type": "score", "instructions": "How much?", "criteria": ["low", "high"]},
                     "matches": {"type": "noul", "instructions": "Does it match?"}}
        raw = {"answers": {"amount": {"type": "score", "score": .8, "probabilities": {"0": .2, "1": .8}},
                           "matches": {"type": "noul", "noul": .05}}}
        parsed = validate_answers(raw, questions)
        self.assertEqual(parsed["matches"]["answer_probability"], .95)
        self.assertEqual(parsed["amount"]["score"], .8)
        bad = copy.deepcopy(raw)
        bad["answers"]["amount"]["score"] = .1
        with self.assertRaises(ValueError):
            validate_answers(bad, questions)


if __name__ == "__main__":
    unittest.main()
