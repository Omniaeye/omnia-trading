# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Bounded byte streams with durable failures and resumable batch boundaries."""
from datetime import datetime, timezone
import hashlib
import json


def consume(source, output, *, limit, max_bytes, ledger, process):
    failures = 0
    number = 0
    while number < limit:
        line = source.readline(max_bytes + 1)
        if not line:
            return failures
        number += 1
        fingerprint = hashlib.sha256(line)
        failure = None
        if len(line) > max_bytes:
            while line and not line.endswith(b'\n'):
                line = source.readline(max_bytes + 1)
                fingerprint.update(line)
            failure = 'INPUT_TOO_LARGE'
        elif not line.strip():
            continue
        else:
            try:
                record = process(json.loads(line.decode('utf-8')))
            except Exception as error:
                failure = type(error).__name__
        if failure:
            failures += 1
            record = ledger.record_assessment({
                'schema': 'omnia.input.failure.v1', 'status': 'failed',
                'line': number, 'error_code': failure,
                'input_sha256': fingerprint.hexdigest(),
                'evaluated_at': datetime.now(timezone.utc).isoformat(),
            })
        output.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
        output.flush()
    # No look-ahead: the first unread record still belongs to the caller.
    paused = {'status': 'paused', 'reason': 'record_limit', 'processed_lines': number,
              'next_line': number + 1}
    try:
        paused['next_offset_bytes'] = source.tell()
    except (OSError, AttributeError):
        pass
    output.write(json.dumps(paused) + '\n')
    output.flush()
    return failures
