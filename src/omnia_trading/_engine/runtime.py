# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Explicit local checkpoint configuration and complete-input inference."""

from __future__ import annotations

import hashlib
import os
import re
import importlib.metadata
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path

from .ledger import probability


@dataclass(frozen=True)
class Settings:
    revision: str
    model: str = "english"
    device: str = "cpu"
    threads: int = 2
    max_len: int = 512
    head_max_len: int = 192
    max_bytes: int = 65536
    min_probability: float = .8
    database: str = "var/omnia/decisions.sqlite3"

    def __post_init__(self):
        if not isinstance(self.revision, str) or not re.fullmatch(r"[0-9a-f]{40}", self.revision):
            raise ValueError("OMNIA_LAYA_REVISION must be an immutable 40-character Hub commit")
        limits = {"english": 512, "typed-decisions": 1024, "multilingual": 8192}
        if any(type(value) is not int for value in (self.threads, self.max_len, self.head_max_len, self.max_bytes)):
            raise ValueError("runtime budgets must be integers")
        if self.model not in limits or self.device not in {"cpu", "cuda", "mps"}:
            raise ValueError("unsupported model or device")
        if not 1 <= self.threads <= 64 or not 128 <= self.max_len <= limits[self.model]:
            raise ValueError("invalid thread count or context size")
        if not 32 <= self.head_max_len < self.max_len or not 1024 <= self.max_bytes <= 1048576:
            raise ValueError("invalid head or byte budget")
        probability(self.min_probability)
        if not isinstance(self.database, str) or not self.database.strip():
            raise ValueError("database path is required")

    @classmethod
    def from_env(cls):
        return cls(
            revision=os.environ.get("OMNIA_LAYA_REVISION", ""),
            model=os.environ.get("OMNIA_LAYA_MODEL", "english"),
            device=os.environ.get("OMNIA_LAYA_DEVICE", "cpu"),
            threads=int(os.environ.get("OMNIA_LAYA_THREADS", "2")),
            max_len=int(os.environ.get("OMNIA_LAYA_MAX_LEN", "512")),
            head_max_len=int(os.environ.get("OMNIA_LAYA_HEAD_MAX_LEN", "192")),
            max_bytes=int(os.environ.get("OMNIA_LAYA_MAX_INPUT_BYTES", "65536")),
            min_probability=float(os.environ.get("OMNIA_LAYA_MIN_PROBABILITY", "0.8")),
            database=os.environ.get("OMNIA_LAYA_DATABASE", "var/omnia/decisions.sqlite3"),
        )


def check_token_budget(tokenizer, state, questions, *, max_len, head_max_len):
    """Reject any state, instruction or option that upstream would truncate."""
    from laya.common import encode_text, render_options, serialize_state

    mask = tokenizer.mask_token

    def size(value):
        return len(encode_text(tokenizer, value.replace(mask, " "), add_special_tokens=False)["input_ids"])

    state_size = size(serialize_state(state))
    for question in questions.values():
        internal = {"t": question["type"], "ins": question["instructions"], "crit": question.get("criteria")}
        options = [size(" " + option) for option in render_options(internal)]
        if any(length > 48 for length in options):
            raise ValueError("a criterion exceeds the checkpoint option budget")
        option_size = sum(length + 1 for length in options)
        instruction_size = size(f"{question['type']} question: {question['instructions']}")
        if head_max_len - option_size < 16 or instruction_size > head_max_len - option_size:
            raise ValueError("question exceeds the checkpoint head budget")
        if 4 + instruction_size + option_size + state_size > max_len:
            raise ValueError("state exceeds the complete-input context budget")


def check_temperatures(agent, questions):
    """Refuse questions whose active checkpoint temperature was corrected on load."""
    from laya.common import QTYPES, temp_bucket
    for question in questions.values():
        kind = QTYPES[question["type"]]
        count = 2 if question["type"] == "noul" else len(question["criteria"])
        bucket = temp_bucket(kind, count)
        raw = agent.temperature_by_options_raw.get(bucket, agent.temperature_raw[kind])
        applied = agent.temperature_by_options.get(bucket, agent.temperature[kind])
        if float(raw) != applied:
            raise ValueError("the active calibration bucket requires review")


class LocalLaya:
    """Lazy local inference; importing this module never loads model weights."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.router = None
        self._manifest = None

    def manifest(self):
        if self._manifest is not None:
            return deepcopy(self._manifest)
        import laya
        root = Path(laya.__file__).resolve().parent
        fingerprint = hashlib.sha256()
        for path in sorted(root.rglob("*.py")):
            fingerprint.update(path.relative_to(root).as_posix().encode())
            fingerprint.update(path.read_bytes())
        integration = hashlib.sha256()
        for name in ("ledger.py", "runtime.py"):
            integration.update(Path(__file__).with_name(name).read_bytes())
        config = asdict(self.settings)
        for key in ("database", "max_bytes", "min_probability"):
            config.pop(key)
        self._manifest = {"backend": "laya.local", "laya_version": laya.__version__,
                "runtime_sha256": fingerprint.hexdigest(), "integration_sha256": integration.hexdigest(),
                "configuration": config,
                "dependencies": {name: importlib.metadata.version(name) for name in ("torch", "transformers", "numpy")},
                "precision": {name: os.environ.get(name, "") for name in
                              ("LAYA_CPU_AMP", "LAYA_CUDA_AMP", "LAYA_MPS_AMP_MIN_ROWS")}}
        return deepcopy(self._manifest)

    def __call__(self, state, questions):
        if self.router is None:
            import torch
            from laya import Router
            torch.set_num_threads(self.settings.threads)
            self.router = Router(device=self.settings.device, revision=self.settings.revision,
                                 default=self.settings.model, auto_task_detection=False, max_loaded=1)
        agent = self.router.load(self.settings.model)
        if agent.revision != self.settings.revision:
            raise ValueError("loaded checkpoint revision differs from the requested revision")
        check_temperatures(agent, questions)
        check_token_budget(agent.tok, state, questions, max_len=self.settings.max_len,
                           head_max_len=self.settings.head_max_len)
        return self.router.predict(state, questions, model=self.settings.model,
                                   max_len=self.settings.max_len, head_max_len=self.settings.head_max_len)
