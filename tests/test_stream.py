# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from helpers import Backend, event
from omnia_trading.cli import run_stream
from omnia_trading.config import Config
from omnia_trading._engine.runtime import Settings
from omnia_trading._engine.ledger import DecisionLedger


class StreamTests(unittest.TestCase):
    def test_environment_example_parses(self):
        root = Path(__file__).resolve().parents[1]
        values = dict(line.split('=', 1) for line in (root / '.env.example').read_text().splitlines()
                      if line and not line.startswith('#'))
        values['OMNIA_LAYA_REVISION'] = 'a' * 40
        with patch.dict(os.environ, values, clear=True):
            config = Config.from_env()
            self.assertEqual(config.max_records, 1000)
            self.assertIn('trading', config.runtime.database)
            self.assertEqual(config.runtime.revision, 'a' * 40)

    def test_record_limit_and_error_recovery(self):
        data = json.dumps(event()).encode() + b'\n'
        source = io.BytesIO(b'{bad\n' + b'x' * 70000 + b'\n' + data + data)
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            ledger = DecisionLedger(Path(folder) / 'test.db')
            try:
                count = run_stream(source, out, Config(Settings('a' * 40), 3), ledger, Backend())
            finally:
                ledger.close()
        rows = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(count, 2)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1]['error_code'], 'INPUT_TOO_LARGE')
        self.assertIn('schema', rows[2])
        self.assertEqual(rows[3]['status'], 'paused')
        self.assertEqual(source.readline(), data)

    def test_utf8_error_does_not_expose_input(self):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            ledger = DecisionLedger(Path(folder) / 'test.db')
            try:
                run_stream(io.BytesIO(b'\xffsecret-value\n'), out, Config(Settings('a' * 40)), ledger, Backend())
            finally:
                ledger.close()
        self.assertNotIn('secret-value', out.getvalue())
        self.assertIn('UnicodeDecodeError', out.getvalue())
