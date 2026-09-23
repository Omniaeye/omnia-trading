# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Bounded JSONL input, explicit results, no background network listener."""
import argparse
import json
import sys
from .config import Config
from .pipeline import process
from ._engine.ledger import DecisionLedger
from ._engine.runtime import LocalLaya


def run_stream(source, output, config, ledger, backend):
    failures = 0
    number = 0
    while True:
        line = source.readline(config.runtime.max_bytes + 1)
        if not line:
            break
        number += 1
        if number > config.max_records:
            output.write(json.dumps({'status': 'failed', 'line': number, 'error_code': 'RECORD_LIMIT'}) + '\n')
            return failures + 1
        if len(line) > config.runtime.max_bytes:
            while line and not line.endswith(b'\n'):
                line = source.readline(config.runtime.max_bytes + 1)
            record = {'status': 'failed', 'line': number, 'error_code': 'INPUT_TOO_LARGE'}
            failures += 1
        elif not line.strip():
            continue
        else:
            try:
                event = json.loads(line.decode('utf-8'))
                record = process(event, ledger, backend, min_probability=config.runtime.min_probability,
                                 max_bytes=config.runtime.max_bytes, policy=config.policy())
            except Exception as error:
                record = {'status': 'failed', 'line': number, 'error_code': type(error).__name__}
                failures += 1
        output.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
        output.flush()
    return failures


def main():
    parser = argparse.ArgumentParser(description='OMNIA Trading decision processing')
    parser.add_argument('--input', default='-', help='JSONL file or - for stdin')
    args = parser.parse_args()
    source = ledger = None
    try:
        config = Config.from_env()
        backend = LocalLaya(config.runtime)
        ledger = DecisionLedger(config.runtime.database)
        source = sys.stdin.buffer if args.input == '-' else open(args.input, 'rb')
        return 1 if run_stream(source, sys.stdout, config, ledger, backend) else 0
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_code': type(error).__name__}), file=sys.stderr)
        return 2
    finally:
        if source is not None and args.input != '-':
            source.close()
        if ledger is not None:
            ledger.close()


if __name__ == '__main__':
    raise SystemExit(main())
