-- ============================================================
-- JARVIS Acadêmico — Migration 001 (initial)
-- Cria as 5 tabelas base + 6 índices. Bumpa user_version para 1.
-- ============================================================

-- ---------- RAG: documents & chunks ----------
CREATE TABLE documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    source_path   TEXT    NOT NULL UNIQUE,
    type          TEXT    NOT NULL CHECK (type IN ('pdf','txt','md')),
    char_count    INTEGER NOT NULL DEFAULT 0,
    chunk_count   INTEGER NOT NULL DEFAULT 0,
    ingested_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE chunks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    text          TEXT    NOT NULL,
    char_start    INTEGER NOT NULL,
    char_end      INTEGER NOT NULL,
    UNIQUE (document_id, position)
);

CREATE INDEX idx_chunks_doc ON chunks(document_id);

-- Tabela vetorial (sqlite-vec virtual table) será criada pelo módulo RAG
-- na Spec 002, conforme padrão da extensão. Schema previsto:
--   CREATE VIRTUAL TABLE chunk_vecs USING vec0(
--       chunk_id INTEGER PRIMARY KEY,
--       embedding FLOAT[384]
--   );

-- ---------- Agenda ----------
CREATE TABLE events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    description  TEXT,
    starts_at    TEXT    NOT NULL,
    ends_at      TEXT,
    kind         TEXT    NOT NULL CHECK (kind IN ('aula','prova','trabalho','outro')),
    location     TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_events_starts_at ON events(starts_at);

-- ---------- Tarefas ----------
CREATE TABLE tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    description  TEXT,
    due_at       TEXT,
    status       TEXT    NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','done')),
    priority     INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_at ON tasks(due_at);

-- ---------- Audit de tool calls ----------
CREATE TABLE tool_call_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL DEFAULT (datetime('now')),
    tool_name   TEXT    NOT NULL,
    input_json  TEXT    NOT NULL,
    output_json TEXT,
    status      TEXT    NOT NULL CHECK (status IN ('ok','error')),
    error_msg   TEXT,
    duration_ms INTEGER NOT NULL,
    llm_call_id TEXT
);

CREATE INDEX idx_tool_call_logs_ts   ON tool_call_logs(ts);
CREATE INDEX idx_tool_call_logs_tool ON tool_call_logs(tool_name);

-- ============================================================
-- O PRAGMA user_version é gerenciado pelo runner em src/core/db.py
-- (linhas que mudam user_version DENTRO de migrations são ignoradas
-- pelo split de statements). Mantemos abaixo como documentação.
-- ============================================================

PRAGMA user_version = 1;
