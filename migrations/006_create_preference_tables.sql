-- Migration: create personalization preference tables
PRAGMA foreign_keys=ON;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS preference_profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    bookmark_count INTEGER NOT NULL DEFAULT 0,
    profile_embedding TEXT,
    category_weights TEXT,
    domain_weights TEXT,
    last_bookmark_id TEXT,
    status TEXT NOT NULL DEFAULT 'ready',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_preference_profiles_user ON preference_profiles(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_preference_profiles_updated_at ON preference_profiles(updated_at);

CREATE TABLE IF NOT EXISTS personalized_scores (
    id TEXT PRIMARY KEY,
    profile_id TEXT,
    user_id TEXT,
    document_id TEXT NOT NULL,
    score REAL NOT NULL CHECK(score >= 0.0 AND score <= 1.0),
    rank INTEGER NOT NULL CHECK(rank >= 1),
    components TEXT,
    explanation TEXT,
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (profile_id) REFERENCES preference_profiles(id) ON DELETE SET NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_personalized_scores_user_document ON personalized_scores(user_id, document_id);
CREATE INDEX IF NOT EXISTS idx_personalized_scores_document ON personalized_scores(document_id);
CREATE INDEX IF NOT EXISTS idx_personalized_scores_score ON personalized_scores(score);

CREATE TABLE IF NOT EXISTS preference_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    document_id TEXT,
    job_type TEXT NOT NULL DEFAULT 'profile_rebuild',
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    last_error TEXT,
    next_attempt_at TEXT,
    scheduled_at TEXT DEFAULT (datetime('now')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    payload TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_preference_jobs_status ON preference_jobs(status);
CREATE INDEX IF NOT EXISTS idx_preference_jobs_next_attempt ON preference_jobs(next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_preference_jobs_job_type ON preference_jobs(job_type);

CREATE TABLE IF NOT EXISTS preference_feedbacks (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    document_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_preference_feedbacks_document ON preference_feedbacks(document_id);
CREATE INDEX IF NOT EXISTS idx_preference_feedbacks_user ON preference_feedbacks(user_id);
CREATE INDEX IF NOT EXISTS idx_preference_feedbacks_created_at ON preference_feedbacks(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_preference_feedbacks_unique_submission ON preference_feedbacks(user_id, document_id, feedback_type);

COMMIT;
