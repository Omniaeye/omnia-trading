# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Extract source-bound ranking trajectories from hash-verified capture receipts."""
import hashlib
import json
import math
from pathlib import Path

from .identity import identity


def asset_key(asset):
    return json.dumps(asset, sort_keys=True)


def ranking_series(source: Path, manifest: dict):
    groups, issues, verified_hashes = {}, [], {}
    seen = set()
    for receipt in sorted(manifest['captures'], key=lambda row: row['received_at']):
        capture_id = receipt['capture_id']
        if capture_id in seen:
            raise ValueError('duplicate_capture_id')
        seen.add(capture_id)
        if receipt['endpoint'] != 'market_rank':
            continue
        raw_path = source / 'raw' / (capture_id + '.json')
        if raw_path.resolve().parent != (source / 'raw').resolve():
            raise ValueError('invalid_capture_path')
        raw = raw_path.read_bytes()
        checksum = hashlib.sha256(raw).hexdigest()
        if checksum != receipt['raw_sha256']:
            raise ValueError('capture_hash_mismatch')
        verified_hashes[capture_id] = checksum
        payload = json.loads(raw)
        if payload.get('code') != 0:
            raise ValueError('capture_provider_error')
        data = payload['data']
        if isinstance(data, dict) and 'code' in data:
            if data['code'] != 0:
                raise ValueError('capture_provider_error')
            data = data['data']
        chain = 'solana' if receipt['chain'] == 'sol' else receipt['chain']
        for index, token in enumerate(data['rank']):
            try:
                token_chain = 'solana' if token.get('chain') == 'sol' else token.get('chain', chain)
                if token_chain != chain:
                    raise ValueError('source_chain_mismatch')
                asset = identity({'chain': chain, 'network_id': 'provider.' + chain,
                                  'contract': token['address'], 'pool': token.get('pool_address') or None})
                price = token.get('price')
                if type(price) not in (int, float) or not math.isfinite(price) or price <= 0:
                    raise ValueError('unusable_source_price')
                key = asset_key(asset)
                if key not in groups:
                    groups[key] = {'id': hashlib.sha256(key.encode()).hexdigest()[:20], 'identity': asset,
                                   'name': str(token.get('symbol') or token.get('name') or 'Token')[:100],
                                   'source': 'market_rank', 'points': [], 'evaluations': []}
                groups[key]['points'].append({'at': receipt['received_at'], 'price': price,
                                             'evidence': f'capture:{capture_id}:rank:{index}', 'capture_id': capture_id})
            except (ValueError, KeyError) as error:
                issues.append({'capture_id': capture_id, 'row': index, 'reason': str(error)})
    return groups, issues, verified_hashes
