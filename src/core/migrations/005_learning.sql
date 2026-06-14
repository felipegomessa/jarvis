-- ============================================================
-- JARVIS Acadêmico — Migration 005 (Melhorias de Aprendizado / Spec 007)
-- Provas eletrônicas geradas a partir de materiais: questões, tentativas,
-- respostas. Alimenta a identificação de dificuldades + plano de estudos.
-- ============================================================

-- Provas geradas a partir de materiais
CREATE TABLE quizzes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'ready',  -- ready | completed
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Documentos-fonte da prova (N:N) — escolha de "vários documentos"
CREATE TABLE quiz_documents (
    quiz_id     INTEGER NOT NULL REFERENCES quizzes(id)   ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (quiz_id, document_id)
);

CREATE TABLE quiz_questions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id            INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    position           INTEGER NOT NULL,
    type               TEXT    NOT NULL,           -- 'mc' | 'open'
    prompt             TEXT    NOT NULL,
    options_json       TEXT,                       -- MC: JSON array de 4 strings
    correct_index      INTEGER,                    -- MC: 0..3
    answer_key         TEXT,                       -- open: rubrica/pontos esperados
    topic              TEXT    NOT NULL DEFAULT '',
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_chunk_id    INTEGER REFERENCES chunks(id)    ON DELETE SET NULL,
    max_points         REAL    NOT NULL DEFAULT 1.0
);
CREATE INDEX idx_quiz_questions_quiz ON quiz_questions(quiz_id);

CREATE TABLE quiz_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id     INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    started_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    score       REAL,                              -- 0..10 (NULL enquanto em curso)
    status      TEXT    NOT NULL DEFAULT 'in_progress'  -- in_progress | graded
);
CREATE INDEX idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);

CREATE TABLE quiz_answers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id     INTEGER NOT NULL REFERENCES quiz_attempts(id)  ON DELETE CASCADE,
    question_id    INTEGER NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    response       TEXT    NOT NULL DEFAULT '',
    awarded_points REAL,
    is_correct     INTEGER,                        -- MC: 0/1; open: NULL
    feedback       TEXT
);
CREATE INDEX idx_quiz_answers_attempt ON quiz_answers(attempt_id);

PRAGMA user_version = 5;
