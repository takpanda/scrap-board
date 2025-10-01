"""Simple script to normalize datetime-like TEXT fields in a SQLite DB to ISO-8601.

This is a safe utility to run locally when you hit parsing errors caused by RFC-2822
strings stored in DATETIME/TEXT columns (e.g. 'Thu, 18 Sep 2025 04:02:17 GMT').

It will attempt to parse values in `documents.published_at`, `documents.fetched_at`,
`documents.created_at`, `documents.updated_at`, and several preference tables, then
rewrite them as RFC3339/ISO-8601 strings so SQLAlchemy's `DateTime` reads them cleanly.

Usage:
    python scripts/sanitize_dates.py /path/to/data/scraps.db

Note: Always back up your DB before running.
"""

import sys
import sqlite3
from dateutil import parser
from datetime import datetime

CANDIDATE_COLUMNS = [
    ("documents", "published_at"),
    ("documents", "fetched_at"),
    ("documents", "created_at"),
    ("documents", "updated_at"),
    ("preference_profiles", "updated_at"),
    ("preference_profiles", "created_at"),
    ("personalized_scores", "computed_at"),
    ("preference_jobs", "next_attempt_at"),
]


def normalize_db(path: str) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    for table, col in CANDIDATE_COLUMNS:
        # check column exists
        try:
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            if col not in cols:
                continue
        except Exception:
            continue

        cur.execute(f"SELECT rowid, {col} FROM {table} WHERE {col} IS NOT NULL")
        rows = cur.fetchall()
        updated = 0
        for rowid, val in rows:
            if not val:
                continue
            if isinstance(val, (int, float)):
                # likely already a timestamp number; skip
                continue
            try:
                dt = parser.parse(val)
                iso = dt.isoformat()
                if iso != val:
                    cur.execute(f"UPDATE {table} SET {col} = ? WHERE rowid = ?", (iso, rowid))
                    updated += 1
            except Exception:
                # skip unparsable
                continue
        if updated:
            print(f"Updated {updated} rows in {table}.{col}")
        conn.commit()

    conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/sanitize_dates.py /path/to/scraps.db")
        sys.exit(2)
    path = sys.argv[1]
    normalize_db(path)
    print("Done.")
