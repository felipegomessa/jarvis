-- ============================================================
-- JARVIS Acadêmico — Migration 002 (rag)
-- Adiciona dedupe por hash e virtual table de vetores.
-- ============================================================

-- D-021: dedupe por hash do conteúdo
ALTER TABLE documents ADD COLUMN content_hash TEXT NOT NULL DEFAULT '';
CREATE INDEX idx_documents_content_hash ON documents(content_hash);

-- D-020 / D-004: vector store (multilingual-e5-small = 384 dim)
CREATE VIRTUAL TABLE chunk_vecs USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);

PRAGMA user_version = 2;
