CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  url TEXT UNIQUE,
  domain TEXT,
  title TEXT NOT NULL,
  author TEXT,
  published_at DATETIME,
  lang TEXT,
  content_md TEXT NOT NULL,
  content_text TEXT NOT NULL,
  hash TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
CREATE INDEX IF NOT EXISTS idx_documents_domain ON documents(domain);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash);