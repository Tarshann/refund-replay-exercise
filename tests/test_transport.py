import concurrent.futures
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from boundary import Boundary, Refund
from destination import initialize
from observe import observe
from transport import Envelope, Transport, sign

# Public deterministic fixtures, not deployment credentials.
KEYS = {'alice-key': ('actor-alice', b'public-fixture-key-alice'),
        'bob-key': ('actor-bob', b'public-fixture-key-bob')}


class TransportGrantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.dest, self.grants, self.nonces = (root / x for x in
                                             ('destination.sqlite','grants.sqlite','nonces.sqlite'))
        initialize(self.dest)
        self.boundary = Boundary(self.grants, self.dest)
        self.boundary.issue('grant', Refund(), 160, actor_id='actor-alice')
        self.transport = Transport(self.nonces, self.boundary, KEYS)

    def envelope(self, nonce, key_id='alice-key', **changes):
        e = Envelope(key_id, nonce, 100, 'grant', Refund(), nonce)
        return sign(replace(e, **changes), KEYS[key_id][1])

    def test_fresh_nonces_same_grant_corrected(self):
        results = [self.transport.receive(self.envelope(n), 100) for n in ('nonce-1','nonce-2')]
        self.assertEqual([r['authenticated'] for r in results], [True, True])
        self.assertEqual([r['decision'] for r in results], ['allowed','reused_grant'])
        self.assertEqual(len(observe(self.dest)), 1)

    def test_fresh_nonces_same_grant_baseline(self):
        self.boundary.corrected = False
        results = [self.transport.receive(self.envelope(n), 100) for n in ('nonce-1','nonce-2')]
        self.assertTrue(all(r['authenticated'] for r in results))
        self.assertEqual([r['decision'] for r in results], ['allowed','allowed'])
        self.assertEqual(len(observe(self.dest)), 2)

    def test_wrong_authenticated_actor_does_not_burn_grant(self):
        result = self.transport.receive(self.envelope('bob-nonce', 'bob-key'), 100)
        self.assertTrue(result['authenticated'])
        self.assertEqual(result['actor_id'], 'actor-bob')
        self.assertEqual(result['decision'], 'wrong_actor')
        self.assertEqual(observe(self.dest), [])
        self.assertEqual(self.transport.receive(self.envelope('alice-nonce'),100)['decision'], 'allowed')

    def test_missing_actor_refused_without_consumption(self):
        for actor in ('', None):
            self.assertEqual(self.boundary.invoke('grant',Refund(),100,'missing',actor_id=actor),
                             'missing_actor')
        self.assertEqual(observe(self.dest), [])
        self.assertEqual(self.transport.receive(self.envelope('valid'),100)['decision'], 'allowed')

    def test_same_transport_nonce_still_refused_in_baseline(self):
        self.boundary.corrected = False
        envelope = self.envelope('same-nonce')
        self.assertEqual(self.transport.receive(envelope,100)['decision'], 'allowed')
        self.assertEqual(self.transport.receive(envelope,100)['decision'], 'transport_replay')
        self.assertEqual(len(observe(self.dest)), 1)

    def test_forged_hmac_cannot_burn_nonce_or_grant(self):
        valid = self.envelope('same-nonce')
        self.assertEqual(self.transport.receive(replace(valid,signature='forged'),100)['decision'],
                         'invalid_transport_signature')
        self.assertEqual(observe(self.dest), [])
        self.assertEqual(self.transport.receive(valid,100)['decision'], 'allowed')

    def test_report_rejects_missing_and_extra_destination_entries(self):
        from unittest.mock import patch
        from destination import refund_handler
        from run import run_transport_lane
        def extra(path, attempt_id, refund):
            refund_handler(path, attempt_id, refund)
            refund_handler(path, 'unexpected', refund)
        for name, handler in [('missing', lambda *args: None), ('extra', extra)]:
            with self.subTest(name=name), patch('destination.refund_handler', side_effect=handler):
                result = run_transport_lane(Path(self.temp.name) / name, True)
            self.assertFalse(result['expectations_match'])

    def test_tampered_identity_or_amount_fails_hmac(self):
        valid = self.envelope('same-nonce')
        for mutated in (replace(valid,key_id='bob-key'),replace(valid,refund=Refund(amount_minor=1001))):
            self.assertEqual(self.transport.receive(mutated,100)['decision'],
                             'invalid_transport_signature')
        self.assertEqual(self.transport.receive(valid,100)['decision'], 'allowed')

    def test_transport_expiry_and_unknown_key(self):
        e=self.envelope('nonce')
        self.assertEqual(self.transport.receive(e,160)['decision'], 'expired_transport_message')
        self.assertEqual(self.transport.receive(e,99)['decision'], 'expired_transport_message')
        self.assertEqual(self.transport.receive(replace(e,key_id='unknown'),100)['decision'],
                         'unknown_transport_key')
        self.assertEqual(observe(self.dest), [])

    def test_concurrent_fresh_nonces_share_one_grant(self):
        def attempt(i):
            b=Boundary(self.grants,self.dest)
            t=Transport(self.nonces,b,KEYS)
            return t.receive(self.envelope(str(i)),100)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(attempt,range(16)))
        self.assertTrue(all(r['authenticated'] for r in results))
        self.assertEqual(sum(r['decision']=='allowed' for r in results),1)
        self.assertEqual(sum(r['decision']=='reused_grant' for r in results),15)
        self.assertEqual(len(observe(self.dest)),1)

    def test_concurrent_same_envelope_claims_nonce_once(self):
        self.boundary.corrected=False
        def attempt(i):
            b=Boundary(self.grants,self.dest,corrected=False)
            return Transport(self.nonces,b,KEYS).receive(self.envelope('same'),100)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(attempt,range(16)))
        self.assertEqual(sum(r['decision']=='allowed' for r in results),1)
        self.assertEqual(sum(r['decision']=='transport_replay' for r in results),15)
        self.assertEqual(len(observe(self.dest)),1)
