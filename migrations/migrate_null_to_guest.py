#!/usr/bin/env python3
"""
Migration script to convert NULL user_id values to 'guest' across all tables.

This script updates:
- bookmarks.user_id
- preference_feedbacks.user_id
- preference_profiles.user_id
- personalized_scores.user_id

Usage:
    python migrations/migrate_null_to_guest.py [--dry-run]
"""
import argparse
import sqlite3
import sys
from pathlib import Path

GUEST_USER_ID = "guest"
DB_PATH = Path("data/scraps.db")

TABLES_TO_MIGRATE = [
    "bookmarks",
    "preference_feedbacks",
    "preference_profiles",
    "personalized_scores",
]


def migrate_table(cursor: sqlite3.Cursor, table_name: str, dry_run: bool = False) -> int:
    """Migrate NULL user_id values to 'guest' in a specific table."""
    
    # First check if the table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    if not cursor.fetchone():
        print(f"  ⚠️  Table '{table_name}' does not exist, skipping.")
        return 0
    
    # Check if user_id column exists
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if "user_id" not in columns:
        print(f"  ⚠️  Table '{table_name}' does not have 'user_id' column, skipping.")
        return 0
    
    # Count rows with NULL user_id
    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE user_id IS NULL")
    null_count = cursor.fetchone()[0]
    
    if null_count == 0:
        print(f"  ✓ Table '{table_name}': no NULL user_id values found.")
        return 0
    
    if dry_run:
        print(f"  🔍 Table '{table_name}': {null_count} rows would be updated (DRY RUN)")
        return null_count
    
    # Special handling for preference_feedbacks to avoid UNIQUE constraint violations.
    # There are two conflict scenarios to handle:
    # 1) Multiple NULL rows for the same (document_id, feedback_type) — these would collide when set to the same user_id.
    # 2) A NULL row that would collide with an existing row that already has user_id = 'guest'.
    if table_name == "preference_feedbacks":
        # 1) Within NULL user_id rows, keep one per (document_id, feedback_type), delete the rest.
        # Use rowid to pick a single survivor deterministically.
        cursor.execute(
            "DELETE FROM preference_feedbacks WHERE user_id IS NULL AND rowid NOT IN ("
            "SELECT MIN(rowid) FROM preference_feedbacks WHERE user_id IS NULL GROUP BY document_id, feedback_type"
            ")"
        )
        deleted_within_null = cursor.rowcount
        if deleted_within_null:
            print(f"  ⚠️  preference_feedbacks: removed {deleted_within_null} duplicate NULL rows within same (document_id,feedback_type)")

        # 2) Remove NULL rows that would duplicate existing 'guest' submissions
        cursor.execute(
            "DELETE FROM preference_feedbacks WHERE user_id IS NULL AND EXISTS ("
            "SELECT 1 FROM preference_feedbacks b WHERE b.user_id = ? AND b.document_id = preference_feedbacks.document_id AND b.feedback_type = preference_feedbacks.feedback_type)",
            (GUEST_USER_ID,)
        )
        deleted_conflicts = cursor.rowcount
        if deleted_conflicts:
            print(f"  ⚠️  preference_feedbacks: removed {deleted_conflicts} NULL rows that would conflict with existing '{GUEST_USER_ID}' rows")
    
    # Special handling for preference_profiles: if a 'guest' profile already exists, remove NULL profiles
    if table_name == "preference_profiles":
        # If there is at least one profile with user_id = 'guest', delete any NULL user_id profiles
        cursor.execute("SELECT COUNT(*) FROM preference_profiles WHERE user_id = ?", (GUEST_USER_ID,))
        guest_count = cursor.fetchone()[0]
        if guest_count > 0:
            cursor.execute("DELETE FROM preference_profiles WHERE user_id IS NULL")
            deleted_profiles = cursor.rowcount
            if deleted_profiles:
                print(f"  ⚠️  preference_profiles: removed {deleted_profiles} NULL profiles because a '{GUEST_USER_ID}' profile exists")

    # Special handling for personalized_scores: remove NULL user_id rows that would conflict with existing guest rows
    if table_name == "personalized_scores":
        # Delete NULL rows where a guest score for the same document already exists
        cursor.execute(
            "DELETE FROM personalized_scores WHERE user_id IS NULL AND EXISTS ("
            "SELECT 1 FROM personalized_scores b WHERE b.user_id = ? AND b.document_id = personalized_scores.document_id)",
            (GUEST_USER_ID,)
        )
        deleted_scores = cursor.rowcount
        if deleted_scores:
            print(f"  ⚠️  personalized_scores: removed {deleted_scores} NULL rows that would conflict with existing '{GUEST_USER_ID}' rows")

    # Perform the update
    cursor.execute(
        f"UPDATE {table_name} SET user_id = ? WHERE user_id IS NULL",
        (GUEST_USER_ID,)
    )

    updated_count = cursor.rowcount
    print(f"  ✓ Table '{table_name}': updated {updated_count} rows (NULL → '{GUEST_USER_ID}')")
    return updated_count


def main():
    parser = argparse.ArgumentParser(
        description="Migrate NULL user_id values to 'guest'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making any modifications"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help=f"Path to SQLite database (default: {DB_PATH})"
    )
    
    args = parser.parse_args()
    
    if not args.db_path.exists():
        print(f"❌ Error: database file not found at {args.db_path}")
        sys.exit(1)
    
    print(f"🔧 Guest User ID Migration")
    print(f"   Database: {args.db_path}")
    print(f"   Mode: {'DRY RUN (no changes will be made)' if args.dry_run else 'LIVE (changes will be committed)'}")
    print()
    
    conn = sqlite3.connect(str(args.db_path))
    cursor = conn.cursor()
    
    total_updated = 0
    
    try:
        for table_name in TABLES_TO_MIGRATE:
            count = migrate_table(cursor, table_name, dry_run=args.dry_run)
            total_updated += count
        
        if not args.dry_run and total_updated > 0:
            conn.commit()
            print()
            print(f"✅ Migration complete: {total_updated} rows updated across {len(TABLES_TO_MIGRATE)} tables.")
        elif args.dry_run and total_updated > 0:
            print()
            print(f"🔍 DRY RUN complete: {total_updated} rows would be updated.")
            print("   Run without --dry-run to apply changes.")
        else:
            print()
            print("✅ No migration needed: all user_id values are already set.")
    
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during migration: {e}")
        sys.exit(2)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
