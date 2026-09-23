import unittest
from helpers import event, datapoint
from omnia_trading.contracts import normalize
from omnia_trading.identity import identity
from omnia_trading.catalog import BY_KEY, GROUPS, PARAMETERS


class ContractTests(unittest.TestCase):
    def test_catalog_covers_five_groups_without_duplicate_keys(self):
        self.assertEqual(len(PARAMETERS), 82)
        self.assertEqual(len(BY_KEY), 82)
        self.assertEqual(set(GROUPS), {x['group'] for x in PARAMETERS})

    def test_chain_and_contract_are_identity(self):
        item = event()['identity']
        first = identity(item)
        item['chain'] = 'robinhood'
        self.assertNotEqual(first, identity(item))
        item['network_id'] = 'other-network'
        self.assertNotEqual(first, identity(item))

    def test_solana_is_case_sensitive_and_decodes_to_32_bytes(self):
        item = {'chain': 'solana', 'network_id': 'mainnet-beta', 'contract': 'So11111111111111111111111111111111111111112', 'pool': None}
        self.assertEqual(identity(item)['contract'], item['contract'])
        item['contract'] = '0' * 32
        with self.assertRaises(ValueError):
            identity(item)

    def test_unknown_chain_and_bad_evm_address(self):
        for change in ({'chain': 'ethereum'}, {'contract': 'USDC'}, {'network_id': ''}):
            with self.assertRaises(ValueError):
                identity({**event()['identity'], **change})

    def test_unknown_fields_are_not_silently_ignored(self):
        item = event()
        item['fields']['unknown'] = datapoint(1)
        with self.assertRaises(ValueError):
            normalize(item)

    def test_null_and_source_scale_are_preserved(self):
        item = event()
        item['fields']['top_10_holder_rate'] = datapoint(None, 'source_scale')
        self.assertIsNone(normalize(item)['fields']['top_10_holder_rate']['value'])

    def test_nonfinite_and_nested_values_are_rejected(self):
        for value in (float('nan'), float('inf'), {}, []):
            item = event()
            item['fields']['price'] = datapoint(value)
            with self.assertRaises((ValueError, TypeError)):
                normalize(item)

    def test_window_and_timestamp_are_explicit(self):
        item = event()
        item['fields']['buys'] = datapoint(180, 'count', window=60)
        self.assertEqual(normalize(item)['fields']['buys']['window_seconds'], 60)
        item['fields']['buys']['window_seconds'] = True
        with self.assertRaises(ValueError):
            normalize(item)
