# v0.2 candidate gate report

## A. Feature Summary
Adds an authenticated transport fixture so fresh message nonces can be tested
against the same single-use approval, plus actor binding at redemption.

## B. Affected Surfaces
Local token issuance/redemption, HMAC transport, report and documentation touched.
Destination observer remains a separate process. External product kernels,
production, signing schemas, tenant controls and public proof services untouched.

## C. Required Gates
D, E, F, G, H, J: semantics, binding, integration, failure/concurrency, observable
outcomes and specialized token controls.

## D. Gate Report
D PASS: transport acceptance and action authority distinguished explicitly.
E PASS for fixture paths: verified key maps to actor; exact scope and atomic
single-use consumption precede handler dispatch. Deliberate baseline and direct
handler bypass remain disclosed.
F PASS locally: original and transport scenarios flow through runner to observer.
G PASS locally: concurrent fresh nonces, same-nonce races, consumed persistence,
invalid HMAC, expiry and dispatch failure tested. Failed dispatch burns authority.
H PARTIAL: machine-readable observations and negative report-oracle tests pass;
independent organizational reproduction remains pending.
J PASS for educational scope: HMAC authenticity precedes atomic nonce claim;
nonce replay and grant reuse are separately tested. Public keys here are fixture
shared secrets, not asymmetric signing or evidence-provenance keys.

## E. Invariant Check
K-1 through K-6, EVI-1 through EVI-7, P-1 through P-4, R-1 through R-5,
GOG-1 through GOG-3 and SE-1 through SE-18 are NOT APPLICABLE as platform-wide
attestations. No such platform is implemented or changed here. Local checked
properties are exact scope/actor binding, consume-before-dispatch, separate nonce
claims and grant consumption, and destination-observation accuracy. This report
is not evidence that external production invariants pass. No signed-evidence,
key rotation, or historical verification claim is made.

## F. Test Coverage
24 unittest cases cover the original 13 cases and new fresh-nonce/same-grant
baseline and corrected paths, wrong authenticated actor, missing actor, HMAC
forgery and field tamper, nonce reuse, expiry/unknown key, concurrent fresh-nonce
and same-envelope races, and missing/unexpected destination report entries.
`python3 run.py` runs tests and checks all four report lanes. No CI result or
third-party reproduction is implied by a local result.

## G. Trust Claim Impact
Only local fixture paths are proven. No complete-route, real-settlement,
distributed-deployment, third-party defect, or independent-adoption claim.
The external-run milestone remains pending.

## H. Final Decision
APPROVED WITH REQUIRED FOLLOW-UPS as an educational candidate. Preserve v0.1;
review and independently reproduce the candidate before a new release.

## I. Next Actions
Verify the exact public branch SHA; review the candidate; independently reproduce
and retain the runner's own outputs. A new release must receive a new tag.
