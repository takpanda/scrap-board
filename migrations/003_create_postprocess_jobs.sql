-- Migration: create postprocess_jobs table

CREATE TABLE IF NOT EXISTS postprocess_jobs (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    last_error TEXT,
    next_attempt_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_postprocess_jobs_document_id ON postprocess_jobs (document_id);
CREATE INDEX IF NOT EXISTS idx_postprocess_jobs_status ON postprocess_jobs (status);
