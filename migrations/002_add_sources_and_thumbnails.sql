-- Migration: Add sources table and thumbnail columns
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- Create sources table if not exists
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  config TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  cron_schedule TEXT,
  last_fetched_at TIMESTAMP
);

-- Add columns to documents table if they do not exist
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so check via user_version trick is not reliable in SQL file.
-- We'll attempt to add columns and ignore errors if they already exist.

ALTER TABLE documents ADD COLUMN source TEXT;
ALTER TABLE documents ADD COLUMN original_url TEXT;
ALTER TABLE documents ADD COLUMN thumbnail_url TEXT;
ALTER TABLE documents ADD COLUMN fetched_at TIMESTAMP;

COMMIT;
PRAGMA foreign_keys=ON;
