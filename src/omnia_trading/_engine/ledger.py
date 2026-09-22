# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Validated, replayable decision records without persisting input text."""

from __future__ import annotations

import hashlib
import copy
import json
import math
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA = "omnia.decision.v1"


class DecisionError(RuntimeError):
    """A processing error whose public message never includes provider text."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def text(value: Any, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("invalid bounded string")
    return value


def probability(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("probability must be a finite number")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("probability must be between zero and one")
    return value


def validate_request(request: dict, max_bytes: int = 65_536) -> None:
    if not isinstance(request, dict) or set(request) != {"id", "state", "questions", "evidence"}:
        raise ValueError("request requires exactly id, state, questions and evidence")
    text(request["id"], 200)
    if not isinstance(request["state"], (str, dict, list)) or not request["state"]:
        raise ValueError("state must be nonempty text or JSON")
    if len(canonical(request).encode("utf-8")) > max_bytes:
        raise ValueError("request exceeds byte limit")
    evidence = request["evidence"]
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 64:
        raise ValueError("one to 64 evidence identifiers are required")
    for item in evidence:
        text(item)
    questions = request["questions"]
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 16:
        raise ValueError("one to 16 questions are required")
    for key, question in questions.items():
        text(key, 80)
        if not isinstance(question, dict) or set(question) - {"type", "instructions", "criteria"}:
            raise ValueError("unsupported question fields")
        text(question.get("instructions"), 2000)
        kind, criteria = question.get("type"), question.get("criteria")
        if kind == "choice":
            if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 16:
                raise ValueError("choice requires two to 16 named options")
            for label, description in criteria.items():
                text(label, 100)
                text(description, 2000)
        elif kind == "score":
            if not isinstance(criteria, list) or not 2 <= len(criteria) <= 16:
                raise ValueError("score requires two to 16 ordered levels")
            for level in criteria:
                text(level, 2000)
        elif kind == "noul":
            if criteria is not None:
                if not isinstance(criteria, dict) or set(criteria) != {"false", "true"}:
                    raise ValueError("noul criteria requires false and true descriptions")
                for description in criteria.values():
                    text(description, 2000)
        else:
            raise ValueError("unsupported question type")


def validate_answers(raw: dict, questions: dict) -> dict:
    answers = raw.get("answers") if isinstance(raw, dict) else None
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError("answer identifiers do not match the questions")
    result = {}
    for key, question in questions.items():
        answer, kind = answers[key], question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise ValueError("answer type mismatch")
        if kind == "noul":
            yes = probability(answer.get("noul"))
            normalized = {"type": kind, "noul": yes, "answer_probability": max(yes, 1 - yes)}
        else:
            criteria = question["criteria"]
            labels = list(criteria) if kind == "choice" else [str(i) for i in range(len(criteria))]
            distribution = answer.get("probabilities")
            if not isinstance(distribution, dict) or set(distribution) != set(labels):
                raise ValueError("answer distribution does not match criteria")
            distribution = {label: probability(distribution[label]) for label in labels}
            # Upstream rounds probabilities to four decimal places.
            if abs(sum(distribution.values()) - 1) > len(labels) * 0.000051:
                raise ValueError("answer distribution must sum to one")
            maximum = max(distribution.values())
            normalized = {"type": kind, "probabilities": distribution, "answer_probability": maximum}
            if kind == "choice":
                chosen = answer.get("choice")
                if chosen not in labels or abs(distribution[chosen] - maximum) > 0.00011:
                    raise ValueError("choice is inconsistent with distribution")
                normalized["choice"] = chosen
            else:
                score = answer.get("score")
                if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
                    raise ValueError("score must be finite")
                expected = sum(i * distribution[str(i)] for i in range(len(labels)))
                if not 0 <= score <= len(labels) - 1 or abs(score - expected) > len(labels) ** 2 * 0.000051:
                    raise ValueError("score is inconsistent with distribution")
                normalized["score"] = score
        if "confidence" in answer:
            normalized["model_confidence"] = probability(answer["confidence"])
        if "answer_confidence" in answer:
            reported = probability(answer["answer_confidence"])
            if abs(reported - normalized["answer_probability"]) > 0.00011:
                raise ValueError("answer confidence is inconsistent with distribution")
        result[key] = normalized
    return result


class DecisionLedger:
    """Serialize local decisions, cache successful records and retain failure types.

    The SQLite transaction covers inference. This deliberately permits one active
    decision per ledger, including across processes; busy callers fail after the
    configured SQLite timeout. Use separate ledgers for independent workers.
    """

    def __init__(self, path: str | Path, *, busy_timeout: float = 30):
        if not math.isfinite(busy_timeout) or not 0 < busy_timeout <= 300:
            raise ValueError("invalid SQLite timeout")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=busy_timeout)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS decisions (key TEXT PRIMARY KEY, record TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS failures (key TEXT NOT NULL, kind TEXT NOT NULL, occurred_at TEXT NOT NULL)")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def decide(self, request: dict, predict: Callable, *, manifest: dict,
               min_probability: float = 0.8, max_bytes: int = 65_536) -> dict:
        validate_request(request, max_bytes)
        request = copy.deepcopy(request)
        manifest = copy.deepcopy(manifest)
        floor = probability(min_probability)
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("an engine manifest is required")
        # A sorted JSON object alone would hide changes to option/question order.
        order = [(key, list(q["criteria"]) if isinstance(q.get("criteria"), dict) else None)
                 for key, q in request["questions"].items()]
        identity = {"schema": SCHEMA, "request": request, "order": order,
                    "state_serialization": json.dumps(request["state"], ensure_ascii=False, allow_nan=False),
                    "engine": manifest, "min_probability": floor}
        key = digest(identity)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT record FROM decisions WHERE key=?", (key,)).fetchone()
            if row:
                self.db.commit()
                return {**json.loads(row[0]), "cache_hit": True}
            started = time.perf_counter()
            response = predict(copy.deepcopy(request["state"]), copy.deepcopy(request["questions"]))
            answers = validate_answers(response, request["questions"])
            review = [name for name, answer in answers.items() if answer["answer_probability"] < floor]
            record = {
                "schema": SCHEMA, "decision_id": key, "source_id": request["id"],
                "input_sha256": digest(request["state"]),
                "questions_sha256": digest({"questions": request["questions"], "order": order}),
                "evidence": request["evidence"], "engine": manifest,
                "policy": {"min_answer_probability": floor},
                "status": "review" if review else "accepted", "review_questions": review,
                "answers": answers, "processed_at": datetime.now(timezone.utc).isoformat(),
                "inference_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            self.db.execute("INSERT INTO decisions VALUES (?,?)", (key, canonical(record)))
            self.db.commit()
            return {**record, "cache_hit": False}
        except Exception as error:
            self.db.rollback()
            self.db.execute("INSERT INTO failures VALUES (?,?,?)",
                            (key, type(error).__name__, datetime.now(timezone.utc).isoformat()))
            self.db.commit()
            raise DecisionError("decision failed; inspect the failure type in the private ledger") from None
