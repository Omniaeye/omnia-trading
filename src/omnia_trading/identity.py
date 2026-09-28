# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Identity uses network and address, never ticker or display name."""
import re
ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def address(value, chain):
    if not isinstance(value, str):
        raise ValueError('address_required')
    if chain in {'robinhood', 'bsc'}:
        if not re.fullmatch(r'0x[0-9a-fA-F]{40}', value):
            raise ValueError('invalid_evm_address')
        return value.lower()
    if chain != 'solana' or not 32 <= len(value) <= 44 or any(c not in ALPHABET for c in value):
        raise ValueError('invalid_solana_address')
    number = 0
    for char in value:
        number = number * 58 + ALPHABET.index(char)
    size = (number.bit_length() + 7) // 8 + len(value) - len(value.lstrip('1'))
    if size != 32:
        raise ValueError('invalid_solana_address')
    return value


def pool_identifier(value, chain):
    """EVM pools may use an address or an opaque bytes32 ID; neither proves a protocol."""
    if chain in {'robinhood', 'bsc'} and isinstance(value, str) and re.fullmatch(r'0x[0-9a-fA-F]{64}', value):
        return value.lower()
    return address(value, chain)


def identity(value):
    if not isinstance(value, dict) or set(value) != {'chain', 'network_id', 'contract', 'pool'}:
        raise ValueError('invalid_identity_fields')
    chain = value['chain']
    if not isinstance(chain, str) or chain not in {'robinhood', 'bsc', 'solana'}:
        raise ValueError('unsupported_chain')
    network = value['network_id']
    if not isinstance(network, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,96}', network):
        raise ValueError('invalid_network_id')
    return {'chain': chain, 'network_id': network,
            'contract': address(value['contract'], chain),
            'pool': pool_identifier(value['pool'], chain) if value['pool'] is not None else None}
