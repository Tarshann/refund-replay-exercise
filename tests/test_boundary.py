import concurrent.futures
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from boundary import Boundary, Refund
from destination import initialize
from observe import observe


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.grants, self.dest = root / 'grants.sqlite', root / 'destination.sqlite'
        initialize(self.dest)
        self.boundary = Boundary(self.grants, self.dest)
        self.refund = Refund()
        self.boundary.issue('fixture-token', self.refund, 160)

    def invoke(self, token='fixture-token', refund=None, now=100, attempt='test'):
        return self.boundary.invoke(token, refund or self.refund, now, attempt)

    def test_authorized_then_replay(self):
        self.assertEqual(self.invoke(), 'allowed')
        self.assertEqual(self.invoke(attempt='replay'), 'reused_grant')
        self.assertEqual(len(observe(self.dest)), 1)

    def test_baseline_reproduces_replay(self):
        self.boundary.corrected = False
        self.assertEqual([self.invoke(), self.invoke()], ['allowed', 'allowed'])
        self.assertEqual(sum(x['amount_minor'] for x in observe(self.dest)), 2000)

    def test_wrong_amount_and_every_scope_field(self):
        for field, value in [('amount_minor', 1001), ('currency', 'EUR'),
                             ('payment_id', 'other'), ('merchant_id', 'other'),
                             ('action', 'transfer')]:
            with self.subTest(field=field):
                self.assertEqual(self.invoke(refund=replace(self.refund, **{field:value})),
                                 'scope_mismatch')
        self.assertEqual(observe(self.dest), [])
        self.assertEqual(self.invoke(), 'allowed')

    def test_missing_and_unknown_token(self):
        for token in (None, '', 3):
            self.assertEqual(self.invoke(token=token), 'missing_token')
        self.assertEqual(self.invoke(token='forged'), 'unknown_token')
        self.assertEqual(observe(self.dest), [])

    def test_expired_including_exact_expiry(self):
        for now in (160, 161):
            self.assertEqual(self.invoke(now=now), 'expired_grant')
        self.assertEqual(observe(self.dest), [])

    def test_malformed_amount(self):
        for value in (True, 1000.0, '1000', 0, -1):
            self.assertEqual(self.invoke(refund=Refund(amount_minor=value)), 'malformed_request')
        self.assertEqual(observe(self.dest), [])

    def test_concurrent_connections_one_dispatch(self):
        def attempt(i):
            b = Boundary(self.grants, self.dest)
            return b.invoke('fixture-token', self.refund, 100, str(i))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(16)))
        self.assertEqual(results.count('allowed'), 1)
        self.assertEqual(results.count('reused_grant'), 15)
        self.assertEqual(len(observe(self.dest)), 1)

    def test_consumption_survives_new_boundary(self):
        self.assertEqual(self.invoke(), 'allowed')
        self.boundary = Boundary(self.grants, self.dest)
        self.assertEqual(self.invoke(), 'reused_grant')
        self.assertEqual(len(observe(self.dest)), 1)

    def test_failed_dispatch_burns_grant(self):
        with patch('destination.refund_handler', side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.invoke()
        self.assertEqual(self.invoke(), 'reused_grant')
        self.assertEqual(observe(self.dest), [])

    def test_missing_grant_store_fails_before_dispatch(self):
        self.grants.unlink()
        with self.assertRaises(sqlite3.OperationalError):
            self.invoke()
        self.assertEqual(observe(self.dest), [])

    def test_observer_sees_direct_bypass(self):
        from destination import refund_handler
        refund_handler(self.dest, 'direct-bypass', self.refund)
        self.assertEqual(observe(self.dest)[0]['attempt_id'], 'direct-bypass')
        # Deliberate proof that this teaching boundary does not close every route.

    def test_runner_fails_on_unexpected_destination_entry(self):
        from destination import refund_handler
        from run import run_lane
        def extra_entry(path, attempt_id, refund):
            refund_handler(path, attempt_id, refund)
            refund_handler(path, 'unexpected-bypass', refund)
        with patch('destination.refund_handler', side_effect=extra_entry):
            result = run_lane(Path(self.temp.name) / 'injected', True)
        self.assertFalse(result['expectations_match'])

    def test_runner_fails_when_handler_does_not_record_entry(self):
        from run import run_lane
        with patch('destination.refund_handler'):
            result = run_lane(Path(self.temp.name) / 'missing', True)
        self.assertFalse(result['expectations_match'])


if __name__ == '__main__':
    unittest.main()
