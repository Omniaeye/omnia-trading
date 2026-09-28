# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Endpoint contracts must not infer sellability from undocumented sentinels."""
import hashlib
import json
import unittest

from omnia_trading.security_source import adapt_security


class SecuritySourceTests(unittest.TestCase):
    def setUp(self):
        self.identity = {'chain': 'bsc', 'network_id': 'provider.bsc', 'contract': '0x' + 'a1' * 20, 'pool': None}
        self.payload = {'address': self.identity['contract'], 'is_honeypot': False,
                        'buy_tax': '0.03', 'sell_tax': '0', 'top_10_holder_rate': '0.8065',
                        'can_sell': 0, 'can_not_sell': 0}
        self.metadata = {'identity': self.identity, 'capture_id': 'test-capture',
                         'requested_at': '2026-09-28T12:00:00+00:00', 'received_at': '2026-09-28T12:00:01+00:00'}

    def adapt(self):
        raw = json.dumps(self.payload).encode()
        return adapt_security(raw, {**self.metadata, 'sha256': hashlib.sha256(raw).hexdigest()})

    def test_documented_ratios_and_observed_boolean(self):
        result = self.adapt()
        fields = result['observation']['fields']
        self.assertAlmostEqual(fields['buy_tax']['value'], .03)
        self.assertFalse(fields['is_honeypot']['value'])
        self.assertEqual(fields['buy_tax']['unit'], 'ratio')
        self.assertEqual(result['source_payload'], self.payload)

    def test_sell_sentinels_do_not_create_a_successful_check(self):
        result = self.adapt()
        self.assertNotIn('sell_simulation_success', result['observation']['fields'])
        self.assertIn('can_sell', result['unprojected_fields'])
        self.assertIn('sell_simulation_success', result['unavailable_strategy_fields'])

    def test_null_honeypot_and_zero_alias_do_not_mean_clear(self):
        self.payload.update(is_honeypot=None, honeypot=0)
        result = self.adapt()
        self.assertNotIn('is_honeypot', result['observation']['fields'])

    def test_robinhood_does_not_inherit_bsc_honeypot_support(self):
        self.identity.update(chain='robinhood', network_id='provider.robinhood')
        self.assertNotIn('is_honeypot', self.adapt()['observation']['fields'])

    def test_solana_authorities_are_not_transfer_state(self):
        self.identity.update(chain='solana', network_id='provider.solana', contract='11111111111111111111111111111111')
        self.payload.update(address=self.identity['contract'], renounced_mint=True, renounced_freeze_account=True)
        fields = self.adapt()['observation']['fields']
        self.assertTrue(fields['renounced_freeze_account']['value'])
        self.assertNotIn('transfer_paused', fields)
        self.assertNotIn('is_honeypot', fields)

    def test_percent_like_magnitude_is_not_rescaled(self):
        self.payload['buy_tax'] = '3'
        result = self.adapt()
        self.assertNotIn('buy_tax', result['observation']['fields'])
        self.assertEqual(result['source_payload']['buy_tax'], '3')

    def test_empty_numeric_or_boolean_string_is_not_zero(self):
        self.payload.update(buy_tax='', sell_tax=True, is_honeypot='false')
        fields = self.adapt()['observation']['fields']
        self.assertNotIn('buy_tax', fields)
        self.assertNotIn('sell_tax', fields)
        self.assertNotIn('is_honeypot', fields)

    def test_no_valid_fields_is_an_explicit_empty_projection(self):
        self.payload = {'address': self.identity['contract'], 'can_sell': 0}
        result = self.adapt()
        self.assertIsNone(result['observation'])
        self.assertEqual(result['status'], 'insufficient')

    def test_response_address_must_match_request(self):
        self.payload['address'] = '0x' + 'b2' * 20
        with self.assertRaisesRegex(ValueError, 'identity_mismatch'):
            self.adapt()

    def test_pool_scope_cannot_be_inherited_from_ranking(self):
        self.identity['pool'] = '0x' + 'b2' * 20
        with self.assertRaisesRegex(ValueError, 'token_scope_requires_null_pool'):
            self.adapt()

    def test_receipt_hash_and_clock_are_required(self):
        raw = json.dumps(self.payload).encode()
        with self.assertRaisesRegex(ValueError, 'hash_mismatch'):
            adapt_security(raw, {**self.metadata, 'sha256': '0' * 64})
        self.metadata['requested_at'] = '2026-09-28T12:00:02+00:00'
        with self.assertRaisesRegex(ValueError, 'invalid_capture_clock'):
            self.adapt()

    def test_duplicate_json_keys_are_rejected(self):
        raw = b'{"is_honeypot":true,"is_honeypot":false}'
        with self.assertRaisesRegex(ValueError, 'duplicate_json_key'):
            adapt_security(raw, {**self.metadata, 'sha256': hashlib.sha256(raw).hexdigest()})

    def test_overflow_in_unmapped_field_is_not_preserved_as_infinity(self):
        raw = b'{"unmapped":1e999}'
        with self.assertRaisesRegex(ValueError, 'nonfinite_json_number'):
            adapt_security(raw, {**self.metadata, 'sha256': hashlib.sha256(raw).hexdigest()})

    def test_response_chain_is_not_overridden(self):
        self.payload['chain'] = 'robinhood'
        with self.assertRaisesRegex(ValueError, 'chain_mismatch'):
            self.adapt()


if __name__ == '__main__':
    unittest.main()
