-- Create bookmarks table
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NULL,
    document_id INTEGER NOT NULL,
    note TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT fk_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_user_document ON bookmarks(user_id, document_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_document ON bookmarks(document_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_created_at ON bookmarks(created_at);

COMMIT;
