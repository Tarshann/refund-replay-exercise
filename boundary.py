"""Educational authorization boundary. No network, processors, or external packages."""
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Refund:
    amount_minor: int = 1000
    currency: str = 'USD'
    payment_id: str = 'synthetic-payment-001'
    merchant_id: str = 'synthetic-merchant-001'
    action: str = 'refund'

    def valid(self):
        return (type(self.amount_minor) is int and self.amount_minor > 0
                and all(type(x) is str and bool(x) for x in
                        (self.currency, self.payment_id, self.merchant_id, self.action)))

    def scope(self):
        return (self.amount_minor, self.currency, self.payment_id,
                self.merchant_id, self.action)


class Boundary:
    def __init__(self, grants_path, destination_path, corrected=True):
        self.grants_path = str(grants_path)
        self.destination_path = str(destination_path)
        self.corrected = corrected
        with sqlite3.connect(self.grants_path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS grants (
                token TEXT PRIMARY KEY, amount_minor INTEGER, currency TEXT,
                payment_id TEXT, merchant_id TEXT, action TEXT,
                expires_at INTEGER, consumed INTEGER NOT NULL DEFAULT 0, actor_id TEXT NOT NULL)''')

    def issue(self, token, refund, expires_at, *, actor_id):
        # Fixed tokens belong only to deterministic local fixtures. Real issuers
        # need authenticated issuance and cryptographically unpredictable secrets.
        if not refund.valid() or type(expires_at) is not int or not token or type(actor_id) is not str or not actor_id:
            raise ValueError('invalid fixture grant')
        with sqlite3.connect(self.grants_path) as db:
            db.execute('INSERT INTO grants VALUES (?,?,?,?,?,?,?,0,?)',
                       (token, *refund.scope(), expires_at, actor_id))

    def invoke(self, token, refund, now, attempt_id, *, actor_id):
        if type(token) is not str or not token:
            return 'missing_token'
        if type(actor_id) is not str or not actor_id:
            return 'missing_actor'
        if not refund.valid() or type(now) is not int:
            return 'malformed_request'
        # SQLite serializes compare-and-consume across connections/processes.
        # Consumption commits BEFORE dispatch. Dispatch failure burns the grant;
        # this is at-most-once dispatch, not exactly-once settlement.
        with sqlite3.connect(self.grants_path, timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM grants WHERE token=?', (token,)).fetchone()
            if row is None:
                return 'unknown_token'
            if actor_id != row[8]:
                return 'wrong_actor'
            if now >= row[6]:
                return 'expired_grant'
            if refund.scope() != tuple(row[1:6]):
                return 'scope_mismatch'
            if self.corrected:
                if row[7]:
                    return 'reused_grant'
                changed = db.execute('UPDATE grants SET consumed=1 WHERE token=? AND consumed=0',
                                     (token,)).rowcount
                if changed != 1:
                    return 'reused_grant'
        # Deliberately vulnerable baseline omits only the consumption step.
        from destination import refund_handler
        refund_handler(self.destination_path, attempt_id, refund)
        return 'allowed'
