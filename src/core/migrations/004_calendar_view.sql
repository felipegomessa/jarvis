-- ============================================================
-- JARVIS Acadêmico — Migration 004 (calendar unified view)
-- View read-only que une eventos e tarefas para visualização
-- unificada no calendário (referência: print do Google Calendar).
-- ============================================================

CREATE VIEW calendar_items_view AS
  SELECT
    'event:' || id        AS item_uid,
    'event'               AS item_type,
    id                    AS source_id,
    title,
    description,
    starts_at,
    ends_at,
    kind                  AS category,
    NULL                  AS status,
    NULL                  AS priority,
    location,
    created_at,
    updated_at
  FROM events
  UNION ALL
  SELECT
    'task:' || id         AS item_uid,
    'task'                AS item_type,
    id                    AS source_id,
    title,
    description,
    due_at                AS starts_at,
    NULL                  AS ends_at,
    NULL                  AS category,
    status                AS status,
    priority              AS priority,
    NULL                  AS location,
    created_at,
    completed_at          AS updated_at
  FROM tasks
  WHERE due_at IS NOT NULL;

PRAGMA user_version = 4;
