"""Local HMAC transport fixture, separate from the approval-grant boundary."""
import hashlib
import hmac
import json
import sqlite3
from dataclasses import asdict, dataclass, replace
from boundary import Refund


@dataclass(frozen=True)
class Envelope:
    key_id: str
    nonce: str
    issued_at: int
    token: str
    refund: Refund
    attempt_id: str
    signature: str = ''

    def canonical(self):
        payload = asdict(self)
        del payload['signature']
        return json.dumps(payload, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False).encode('utf-8')


def sign(envelope, key):
    return replace(envelope, signature=hmac.new(key, envelope.canonical(),
                                               hashlib.sha256).hexdigest())


class Transport:
    def __init__(self, path, boundary, trusted_keys, acceptance_window=60):
        self.path = str(path)
        self.boundary = boundary
        # Server-owned map: key ID -> (authenticated actor, key bytes).
        # Actor identity never comes from an unsigned request field.
        self.trusted_keys = dict(trusted_keys)
        self.acceptance_window = acceptance_window
        with sqlite3.connect(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS nonces (
                key_id TEXT, nonce TEXT, PRIMARY KEY(key_id, nonce))''')

    def receive(self, envelope, now):
        def result(decision, authenticated=False, actor=None):
            return {'decision': decision, 'authenticated': authenticated,
                    'actor_id': actor, 'nonce': envelope.nonce}
        if (type(envelope.nonce) is not str or not envelope.nonce
                or type(envelope.key_id) is not str
                or type(envelope.signature) is not str
                or type(envelope.issued_at) is not int or type(now) is not int
                or not isinstance(envelope.refund, Refund) or not envelope.refund.valid()):
            return result('malformed_envelope')
        identity = self.trusted_keys.get(envelope.key_id)
        if identity is None:
            return result('unknown_transport_key')
        actor, key = identity
        try:
            expected = hmac.new(key, envelope.canonical(), hashlib.sha256).hexdigest()
        except (TypeError, ValueError):
            return result('malformed_envelope')
        if (len(envelope.signature) != 64
                or any(c not in '0123456789abcdef' for c in envelope.signature)
                or not hmac.compare_digest(expected, envelope.signature)):
            return result('invalid_transport_signature')
        if envelope.issued_at > now or now - envelope.issued_at >= self.acceptance_window:
            return result('expired_transport_message')
        # Authenticate first; atomically claim nonce before grant redemption.
        # Retain fixture nonces indefinitely; do not prune inside acceptance TTL.
        with sqlite3.connect(self.path, timeout=10) as db:
            try:
                db.execute('INSERT INTO nonces VALUES (?,?)',
                           (envelope.key_id, envelope.nonce))
            except sqlite3.IntegrityError:
                return result('transport_replay', True, actor)
        decision = self.boundary.invoke(envelope.token, envelope.refund, now,
                                        envelope.attempt_id, actor_id=actor)
        return result(decision, True, actor)
