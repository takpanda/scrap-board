-- Add summary columns to documents table
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

ALTER TABLE documents ADD COLUMN short_summary TEXT;
ALTER TABLE documents ADD COLUMN medium_summary TEXT;
ALTER TABLE documents ADD COLUMN summary_generated_at TEXT;
ALTER TABLE documents ADD COLUMN summary_model TEXT;

COMMIT;
PRAGMA foreign_keys=on;
