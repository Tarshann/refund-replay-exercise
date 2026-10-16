"""One-command deterministic exercise and destination-outcome comparison."""
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from boundary import Boundary, Refund
from destination import initialize
from transport import Envelope, Transport, sign

ROOT = Path(__file__).resolve().parent
NOW = 1800000000  # Fixture clock; never wall time.
KEYS = {'alice-key': ('actor-alice', b'public-fixture-key-alice'),
        'bob-key': ('actor-bob', b'public-fixture-key-bob')}


def run_transport_lane(root, corrected):
    root.mkdir()
    destination = root / 'destination.sqlite'
    initialize(destination)
    boundary = Boundary(root / 'grants.sqlite', destination, corrected)
    refund = Refund()
    boundary.issue('shared-grant', refund, NOW + 60, actor_id='actor-alice')
    transport = Transport(root / 'transport.sqlite', boundary, KEYS)
    requests = [('wrong-actor', 'bob-key', 'bob-nonce'),
                ('authorized-fresh-nonce', 'alice-key', 'nonce-1'),
                ('same-grant-fresh-nonce', 'alice-key', 'nonce-2'),
                ('same-message-replay', 'alice-key', 'nonce-2')]
    results = []
    # The last entry repeats the exact second signed message, not just its nonce.
    envelope = None
    for attempt, key_id, nonce in requests:
        if attempt != 'same-message-replay':
            envelope = sign(Envelope(key_id, nonce, NOW, 'shared-grant', refund, attempt),
                            KEYS[key_id][1])
        result = transport.receive(envelope, NOW)
        results.append({'attempt_id': attempt, 'grant_id': 'shared-grant', **result})
    observed = json.loads(subprocess.check_output(
        [sys.executable, str(ROOT / 'observe.py'), str(destination)], text=True))
    expected = ['wrong_actor', 'allowed',
                'reused_grant' if corrected else 'allowed', 'transport_replay']
    expected_entries = ['authorized-fresh-nonce']
    if not corrected:
        expected_entries.append('same-grant-fresh-nonce')
    passed = ([r['decision'] for r in results] == expected
              and all(r['authenticated'] for r in results)
              and [r['actor_id'] for r in results] ==
                  ['actor-bob', 'actor-alice', 'actor-alice', 'actor-alice']
              and [r['nonce'] for r in results] ==
                  ['bob-nonce', 'nonce-1', 'nonce-2', 'nonce-2']
              and [r['attempt_id'] for r in observed] == expected_entries
              and all(tuple(r[k] for k in ('amount_minor', 'currency', 'payment_id',
                                           'merchant_id', 'action')) == refund.scope()
                      for r in observed))
    return {'expectations_match': passed, 'requests': results,
            'destination_handler_entries': observed,
            'handler_entry_count': len(observed),
            'total_synthetic_amount_minor': sum(r['amount_minor'] for r in observed)}


def run_lane(root, corrected):
    root.mkdir()
    destination = root / 'destination.sqlite'
    initialize(destination)
    boundary = Boundary(root / 'grants.sqlite', destination, corrected)
    refund = Refund()
    boundary.issue('fixture-only-grant', refund, NOW + 60, actor_id='actor-alice')
    boundary.issue('fixture-expired-grant', refund, NOW, actor_id='actor-alice')
    attempts = [
        ('wrong-amount', 'fixture-only-grant', Refund(amount_minor=1001)),
        ('authorized', 'fixture-only-grant', refund),
        ('replay', 'fixture-only-grant', refund),
        ('expired', 'fixture-expired-grant', refund),
        ('missing-token', None, refund),
    ]
    decisions = [{'attempt_id': name, 'decision': boundary.invoke(token, request, NOW, name, actor_id='actor-alice')}
                 for name, token, request in attempts]
    # Fresh process reads the destination DB without the boundary object/results.
    observed = json.loads(subprocess.check_output(
        [sys.executable, str(ROOT / 'observe.py'), str(destination)], text=True))
    expected_decisions = ['scope_mismatch', 'allowed',
                          'reused_grant' if corrected else 'allowed',
                          'expired_grant', 'missing_token']
    expected_entries = ['authorized'] if corrected else ['authorized', 'replay']
    passed = ([x['decision'] for x in decisions] == expected_decisions
              and [x['attempt_id'] for x in observed] == expected_entries
              and all(tuple(x[k] for k in ('amount_minor','currency','payment_id',
                                            'merchant_id','action')) == refund.scope()
                      for x in observed))
    return {'expectations_match': passed, 'decisions': decisions,
            'destination_handler_entries': observed, 'handler_entry_count': len(observed),
            'total_synthetic_amount_minor': sum(x['amount_minor'] for x in observed)}


def main():
    tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                           cwd=ROOT)
    if tests.returncode:
        return tests.returncode
    with tempfile.TemporaryDirectory(prefix='refund-replay-') as temp:
        lanes = {name: run_lane(Path(temp) / name, fixed) for name, fixed in
                 [('baseline', False), ('corrected', True)]}
        transport_lanes = {name: run_transport_lane(Path(temp) / ('transport-' + name), fixed)
                           for name, fixed in [('baseline', False), ('corrected', True)]}
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(ROOT.rglob('*')) if p.is_file()
               and '.git' not in p.parts and '__pycache__' not in p.parts
               and p.suffix in ('.py', '.md')}
    report = {'report_schema': 'refund-replay-observation/v2', 'release': 'v0.2-candidate',
              'python': platform.python_version(), 'fixture_clock': NOW,
              'observer': 'separate process; local read-only destination SQLite query',
              'external_maintainer_run': False,
              'scope': 'local synthetic handler entries only; unsigned self-generated report',
              'source_sha256': sources, 'lanes': lanes, 'transport_lanes': transport_lanes,
              'passed': all(x['expectations_match'] for x in
                            [*lanes.values(), *transport_lanes.values()])}
    output = ROOT / 'report.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
