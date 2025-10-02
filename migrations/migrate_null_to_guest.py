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
