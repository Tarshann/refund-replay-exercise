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

ROOT = Path(__file__).resolve().parent
NOW = 1800000000  # Fixture clock; never wall time.


def run_lane(root, corrected):
    root.mkdir()
    destination = root / 'destination.sqlite'
    initialize(destination)
    boundary = Boundary(root / 'grants.sqlite', destination, corrected)
    refund = Refund()
    boundary.issue('fixture-only-grant', refund, NOW + 60)
    boundary.issue('fixture-expired-grant', refund, NOW)
    attempts = [
        ('wrong-amount', 'fixture-only-grant', Refund(amount_minor=1001)),
        ('authorized', 'fixture-only-grant', refund),
        ('replay', 'fixture-only-grant', refund),
        ('expired', 'fixture-expired-grant', refund),
        ('missing-token', None, refund),
    ]
    decisions = [{'attempt_id': name, 'decision': boundary.invoke(token, request, NOW, name)}
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
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(ROOT.rglob('*')) if p.is_file()
               and '.git' not in p.parts and '__pycache__' not in p.parts
               and p.suffix in ('.py', '.md')}
    report = {'report_schema': 'refund-replay-observation/v1', 'release': 'v0.1',
              'python': platform.python_version(), 'fixture_clock': NOW,
              'observer': 'separate process; local read-only destination SQLite query',
              'external_maintainer_run': False,
              'scope': 'local synthetic handler entries only; unsigned self-generated report',
              'source_sha256': sources, 'lanes': lanes,
              'passed': all(x['expectations_match'] for x in lanes.values())}
    output = ROOT / 'report.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
