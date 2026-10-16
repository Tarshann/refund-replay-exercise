# Design and limits — v0.2 candidate

This is an original, standalone teaching exercise. It contains no copied vendor
implementation and does not implement or change any external signed schema.

## Boundary

Trusted local fixture issuance registers an opaque token and exact scope in
SQLite, including the authorized actor. Both paths validate token existence, expiry (now >= expiry refuses),
strict integer minor units, and the full refund scope and actor identity. The baseline intentionally
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

## Transport and actor trust boundary

The public deterministic HMAC fixture keys map to actor-alice and actor-bob in a
server-owned registry. Key ID, nonce, timestamp, token, full refund arguments and
attempt ID are covered by sorted, compact JSON and HMAC-SHA256. The verified
registry mapping, not an actor parameter from a message, supplies the actor to
the approval boundary. Direct `Boundary.invoke` is an internal interface whose
caller must supply a trusted authenticated actor; it is not exposed as a network API.

Transport verification checks HMAC before atomically inserting (key ID, nonce)
into a separate persistent store. New nonces do not create new grants. Consumed
transport identifiers are retained for the entire fixture database lifetime.
Missing stores and storage failures propagate errors; no fail-open fallback exists.
The clock is fixed, future timestamps are refused, and the 60-second acceptance
boundary is exclusive. Public fixture secrets and identity provisioning are not
production authentication. This does not recreate any third-party implementation.

Wrong-actor checks precede grant consumption, so a valid actor-bob envelope cannot
burn actor-alice's grant. A rightful actor retry with another valid message still
fails once the grant was consumed. A refused grant attempt may consume its own
transport nonce; transport acceptance is distinct from approval or handler success.

The two database transactions do not constitute a distributed transaction, and
the demonstration does not provide a multi-server deployment. Each receiver must
use the same trusted key registry, transport store, and grant store for these
local shared-state properties to apply. Threaded tests use independent SQLite
connections. No copied old database, v1 record, or production migration is used.
Report v2 is additive in scenario coverage, with explicit schema/version labeling;
v0.1 remains available at its original tag.
