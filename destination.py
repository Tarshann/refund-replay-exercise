"""Synthetic destination: independently persisted handler entries, not decisions."""
import sqlite3


def initialize(path):
    with sqlite3.connect(str(path)) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS handler_entries (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id TEXT,
            amount_minor INTEGER, currency TEXT, payment_id TEXT,
            merchant_id TEXT, action TEXT)''')


def refund_handler(path, attempt_id, refund):
    with sqlite3.connect(str(path), timeout=10) as db:
        db.execute('''INSERT INTO handler_entries
            (attempt_id,amount_minor,currency,payment_id,merchant_id,action)
            VALUES (?,?,?,?,?,?)''', (attempt_id, *refund.scope()))
