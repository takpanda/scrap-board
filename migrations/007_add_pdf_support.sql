-- Add PDF support to documents table
-- This migration adds pdf_path column to store relative paths for downloaded PDFs
-- Primarily used for SpeakerDeck presentations but applicable to any PDF content

PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

-- Add pdf_path column to store relative paths like "assets/pdfs/speakerdeck/{document_id}.pdf"
-- NULL indicates no PDF is available for this document
ALTER TABLE documents ADD COLUMN pdf_path TEXT;

COMMIT;
PRAGMA foreign_keys=on;

-- Create partial index for efficient queries on documents with PDFs
-- Only indexes non-NULL values to save space and improve performance
CREATE INDEX IF NOT EXISTS idx_documents_pdf_path ON documents(pdf_path) WHERE pdf_path IS NOT NULL;
