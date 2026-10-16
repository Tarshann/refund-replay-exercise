# Refund Replay Exercise

A valid, unexpired authorization can still be replayable. This local exercise
contrasts two paths for a synthetic **$10.00 USD** refund. Both bind amount,
currency, payment, merchant, and action; only the corrected path atomically
consumes the grant before dispatch. MIT licensed; no product, account, package
installation, API key, network service, or real money is involved.

## Run (Python 3.10+, under five minutes)

```sh
git clone https://github.com/Tarshann/refund-replay-exercise.git
cd refund-replay-exercise
git checkout v0.1
python3 run.py
```

On Windows use `py -3 run.py`. From an extracted archive, run `python3 run.py`.
The command runs tests, exits nonzero on failure, and writes `report.json`.

| Attempt | Baseline | Corrected | Destination entries (baseline / corrected) |
| --- | --- | --- | --- |
| Wrong amount ($10.01) | Refused | Refused | 0 / 0 |
| Authorized $10.00 | Allowed | Allowed | 1 / 1 |
| Reuse before expiry | Allowed | Refused | 1 / 0 |
| Expired grant | Refused | Refused | 0 / 0 |
| Missing token | Refused | Refused | 0 / 0 |

Expected totals: baseline **2 entries / 2000 cents**; corrected **1 entry / 1000
cents**; `passed: true`. The baseline vulnerability is reproduced intentionally.
Each lane starts with fresh databases. Fixed tokens and clock make the inputs
deterministic; tokens are test fixtures, never deployment credentials.

## What it proves

For these enumerated local invocations, the baseline accepts reuse and the
corrected boundary consumes authority once. A separate observer process reads
the synthetic destination database, independent of boundary verdicts, to check
whether its handler recorded entry. Tests include scope mutation, expiry,
malformed inputs, concurrent connections, restart persistence, and dispatch
failure. The report includes source hashes. See [DESIGN.md](DESIGN.md).

## What it does not prove

It does not prove every route is closed, real processor settlement, distributed
replay protection, full MCP protocol conformance, production suitability, or a
need for any vendor. The handler is directly callable; a test demonstrates that
limitation. The observer shares the local machine and is not an independent
organization or tamper-proof witness. Consumption before dispatch can lose an
operation on failure; this is at-most-once dispatch, not exactly-once effects.
The report is unsigned and is not Signed Evidence or a certification.

## Record your own result

File an issue here with the exact `git rev-parse HEAD`, Python/OS, command,
exit status, `report.json`, and whether the distinction is already covered by
your toolkit or exposes a gap. Describe failures and changes as well as passes.
The generated report defaults to `external_maintainer_run: false`; a maintainer's
own written account establishes independence, not a flag or a passing local run.
