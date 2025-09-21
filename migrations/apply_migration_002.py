#!/usr/bin/env python3
"""Safely apply migration 002: create `sources` table if missing and add missing columns to `documents`.
This script is idempotent and prints resulting table schemas.
"""
import sqlite3
from pathlib import Path
import sys

DB = Path("data/scraps.db")
if not DB.exists():
    print(f"Error: database file not found at {DB}")
    sys.exit(2)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

# Create sources table if not exists
create_sources_sql = '''
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  config TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  cron_schedule TEXT,
  last_fetched_at TIMESTAMP
);
'''
cur.execute(create_sources_sql)
print("Ensured `sources` table exists (CREATE TABLE IF NOT EXISTS used).")

# Ensure documents table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents';")
if not cur.fetchone():
    print("Error: `documents` table does not exist in the database. Aborting to avoid schema creation surprises.")
    conn.close()
    sys.exit(3)

# Columns we want to ensure exist
columns = {
    'source': 'TEXT',
    'original_url': 'TEXT',
    'thumbnail_url': 'TEXT',
    'fetched_at': 'TIMESTAMP'
}

cur.execute("PRAGMA table_info(documents);")
existing = [row[1] for row in cur.fetchall()]

added = []
for col, coltype in columns.items():
    if col in existing:
        print(f"Column `{col}` already exists; skipping.")
    else:
        sql = f"ALTER TABLE documents ADD COLUMN {col} {coltype};"
        try:
            cur.execute(sql)
            added.append(col)
            print(f"Added column `{col}` ({coltype}).")
        except sqlite3.OperationalError as e:
            print(f"Failed to add column `{col}`: {e}")

conn.commit()

# Print resulting schemas
print('\nPRAGMA table_info(documents);')
cur.execute("PRAGMA table_info(documents);")
for row in cur.fetchall():
    print(row)

print('\nPRAGMA table_info(sources);')
cur.execute("PRAGMA table_info(sources);")
for row in cur.fetchall():
    print(row)

conn.close()

if added:
    print(f"\nMigration applied: added columns: {added}")
else:
    print('\nMigration applied: no columns added (already up-to-date).')
