# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Bounded JSONL input, explicit results, no background network listener."""
import argparse
import json
import sys
from .config import Config
from .stream import consume
from .pipeline import process
from ._engine.ledger import DecisionLedger
from ._engine.runtime import LocalLaya


def run_stream(source, output, config, ledger, backend):
    return consume(source, output, limit=config.max_records, max_bytes=config.runtime.max_bytes,
                   ledger=ledger, process=lambda event: process(
                       event, ledger, backend, min_probability=config.runtime.min_probability,
                       max_bytes=config.runtime.max_bytes, policy=config.policy()))


def main():
    parser = argparse.ArgumentParser(description='OMNIA Trading decision processing')
    parser.add_argument('--catalog', action='store_true', help='Print the executable parameter catalog without loading a model')
    parser.add_argument('--input', default='-', help='JSONL file or - for stdin')
    parser.add_argument('--offset-bytes', type=int, default=0, help='Resume a file at a previous batch byte offset')
    args = parser.parse_args()
    if args.catalog:
        from .catalog import PARAMETERS, CATALOG_VERSION, CATALOG_SHA256
        print(json.dumps({'schema': CATALOG_VERSION, 'sha256': CATALOG_SHA256, 'parameters': PARAMETERS}, ensure_ascii=False, indent=2))
        return 0
    if args.offset_bytes < 0 or (args.input == '-' and args.offset_bytes):
        parser.error('offset requires a file and a nonnegative byte offset')
    source = ledger = None
    try:
        config = Config.from_env()
        backend = LocalLaya(config.runtime)
        ledger = DecisionLedger(config.runtime.database)
        source = sys.stdin.buffer if args.input == '-' else open(args.input, 'rb')
        if args.offset_bytes:
            source.seek(args.offset_bytes)
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
