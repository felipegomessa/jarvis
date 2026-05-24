-- ============================================================
-- JARVIS Acadêmico — Migration 003 (chat sessions)
-- Persiste conversas inteiras para restauração via sidebar "Recentes".
-- ============================================================

CREATE TABLE chat_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_chat_sessions_updated ON chat_sessions(updated_at DESC);

CREATE TABLE chat_messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role          TEXT    NOT NULL CHECK (role IN ('user','assistant','system','tool')),
    content       TEXT    NOT NULL,
    metadata_json TEXT,
    position      INTEGER NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (session_id, position)
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);

PRAGMA user_version = 3;
