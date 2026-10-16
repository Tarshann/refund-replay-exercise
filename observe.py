"""Read only destination observer; never trusts boundary allow/refuse results."""
import json
import sqlite3
import sys
from pathlib import Path


def observe(path):
    uri = Path(path).resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute('SELECT * FROM handler_entries ORDER BY sequence')]


if __name__ == '__main__':
    print(json.dumps(observe(sys.argv[1]), indent=2))
