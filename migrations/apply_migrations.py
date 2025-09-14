#!/usr/bin/env python3
"""Simple migration applier for local development (SQLite).

Usage:
  python migrations/apply_migrations.py --db ./data/scraps.db

This script applies all `migrations/*.sql` files in lexical order.
"""
import argparse
import glob
import os
import sqlite3


def apply_migration(db_path: str, sql_path: str):
    print(f"Applying {os.path.basename(sql_path)} to {db_path}")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="./data/scraps.db", help="Path to SQLite DB")
    args = p.parse_args()

    migrations = sorted(glob.glob(os.path.join("migrations", "*.sql")))
    if not migrations:
        print("No migrations found.")
        return

    if not os.path.exists(args.db):
        print(f"Database {args.db} not found. Exiting.")
        return

    for m in migrations:
        apply_migration(args.db, m)

    print("Migrations applied.")


if __name__ == "__main__":
    main()
