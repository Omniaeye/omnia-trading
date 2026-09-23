from datetime import datetime, timezone


def datapoint(value, unit='USD', evidence='source:one', window=None):
    return {'value': value, 'unit': unit, 'window_seconds': window,
            'observed_at': datetime.now(timezone.utc).isoformat(), 'evidence': evidence}


def event():
    return {'id': 'record-1', 'source': 'contract-test', 'observed_at': datetime.now(timezone.utc).isoformat(),
            'identity': {'chain': 'bsc', 'network_id': '56', 'contract': '0x' + '1' * 40, 'pool': None},
            'fields': {'market_cap': datapoint(50000), 'liquidity': datapoint(20000),
                       'is_honeypot': datapoint(False, 'boolean')}}


class Backend:
    def __init__(self, choice='usable'):
        self.choice = choice
        self.calls = 0

    def manifest(self):
        return {'contract_test_backend': 1, 'choice': self.choice}

    def __call__(self, state, questions):
        self.calls += 1
        return {'answers': {'quality': {'type': 'choice', 'choice': self.choice,
                'probabilities': {key: .9 if key == self.choice else .05 for key in ('usable', 'inconsistent', 'insufficient')}}}}
