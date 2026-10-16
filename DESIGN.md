# Design and limits — v0.1

This is an original, standalone teaching exercise. It contains no copied vendor
implementation and does not implement or change any external signed schema.

## Boundary

Trusted local fixture issuance registers an opaque token and exact scope in
SQLite. Both paths validate token existence, expiry (now >= expiry refuses),
strict integer minor units, and the full refund scope. The baseline intentionally
omits consumption. The corrected path uses BEGIN IMMEDIATE and conditional UPDATE
to persist consumption before the handler is called. Multiple processes sharing
this same database use SQLite locking; separate databases do not share authority.
There is no automatic retry, reissue, authentication, revocation, or policy engine.
Real time and untrusted token issuance are outside this deterministic fixture.

## Destination and observation

The handler writes to its own SQLite database. A fresh observer subprocess opens
it read-only and returns every handler entry, including attempt ID and full scope.
The runner compares that output against explicit expectations, separately from
checking decisions. An empty ledger only establishes no recorded handler entry
in this instrumented local destination, not absence of arbitrary real-world effects.
This is process separation, not an independently administered witness.

## Failure model

A malformed request refuses before dispatch. Missing or unusable storage raises
an error rather than reporting authorization success. Consumption is durable before
dispatch; a handler failure burns authority and may require manual reconciliation.
There is deliberately no claim of transaction atomicity across grant and destination
stores. Crash recovery, replicated state, clock synchronization, real payment
idempotency, complete route coverage, and hostile-host resistance require more work.

## External result acceptance

An independent maintainer must run an exact commit, preserve command/environment,
and write their own observed result in an issue, discussion, or retained email.
Stars, acknowledgments, an assistant's run, and a green test summary are insufficient.
No claim about another project's gap is made until that project's maintainer evaluates it.
