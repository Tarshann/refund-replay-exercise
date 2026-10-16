# Refund Replay Exercise — v0.2 candidate

A valid, unexpired authorization can still be replayable. This local exercise
contrasts two paths for a synthetic **$10.00 USD** refund. Both bind the authenticated actor, amount,
currency, payment, merchant, and action; only the corrected path atomically
consumes the grant before dispatch. MIT licensed; no product, account, package
installation, API key, network service, or real money is involved.

## Run (Python 3.10+, under five minutes)

```sh
git clone --branch feat/grant-vs-transport-replay https://github.com/Tarshann/refund-replay-exercise.git
cd refund-replay-exercise
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

## Authenticated transport versus approval consumption

The new `transport_lanes` report exercises signed HMAC envelopes separately from
the approval boundary. A server-owned key registry resolves the authenticated
actor; the request cannot assert its own identity. Both lanes atomically claim
authenticated transport nonces in a separate SQLite store. Only the corrected
boundary consumes the actor-bound approval grant.

| Authenticated request (same grant) | Baseline | Corrected |
| --- | --- | --- |
| Wrong actor, own valid key, fresh nonce | Wrong actor; no handler entry | Wrong actor; no handler entry |
| Rightful actor, nonce-1 | Allowed | Allowed |
| Rightful actor, nonce-2 | Allowed again | Refused: reused grant |
| Repeat exact nonce-2 message | Transport replay refused | Transport replay refused |

Both fresh-nonce messages authenticate. Expected destination totals remain two
$10 entries versus one. Wrong-actor refusal does not burn the rightful actor's
grant. A forged HMAC cannot burn either nonce or grant. The report records actors,
nonces, decisions and separately observed destination entries. This is an original
local fixture, not an adapter or test of any third-party toolkit.

The published `v0.1` tag is unchanged. This branch is a v0.2 candidate; no v0.2
release is claimed. Report schema is `refund-replay-observation/v2`. Old fixture
databases are not migrated: the runner always starts fresh temporary databases.

## What it proves

For these enumerated local invocations, the baseline accepts reuse and the
corrected boundary consumes authority once. A separate observer process reads
the synthetic destination database, independent of boundary verdicts, to check
whether its handler recorded entry. Tests include authenticated actor mismatch, fresh-nonce grant reuse, scope mutation, expiry,
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
