"""Testes de integração para log_tool_call — T-001.14."""

from __future__ import annotations

import json
import re
import sqlite3

import pytest

from src.core.db import log_tool_call


def test_log_tool_call_inserts_and_returns_lastrowid(tmp_db: sqlite3.Connection) -> None:
    input_json = json.dumps({"query": "regressão logística", "top_k": 3})
    output_json = json.dumps({"chunks": [1, 2, 3]})
    rid = log_tool_call(
        conn=tmp_db,
        tool_name="buscar_material_rag",
        input_json=input_json,
        output_json=output_json,
        status="ok",
        error_msg=None,
        duration_ms=120,
    )
    assert rid > 0

    row = tmp_db.execute(
        "SELECT id, ts, tool_name, input_json, output_json, status, "
        "error_msg, duration_ms, llm_call_id FROM tool_call_logs WHERE id = ?",
        (rid,),
    ).fetchone()
    assert row is not None
    assert row["tool_name"] == "buscar_material_rag"
    assert row["status"] == "ok"
    assert row["duration_ms"] == 120
    assert row["input_json"] == input_json
    assert row["output_json"] == output_json
    assert row["error_msg"] is None
    assert row["llm_call_id"] is None


def test_log_tool_call_timestamp_is_iso_utc_with_z(tmp_db: sqlite3.Connection) -> None:
    rid = log_tool_call(
        conn=tmp_db,
        tool_name="x",
        input_json="{}",
        output_json="{}",
        status="ok",
        error_msg=None,
        duration_ms=1,
    )
    row = tmp_db.execute(
        "SELECT ts FROM tool_call_logs WHERE id = ?", (rid,)
    ).fetchone()
    ts = row["ts"]
    # ex: 2026-05-23T18:34:56Z
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", ts), ts


def test_log_tool_call_with_error_status(tmp_db: sqlite3.Connection) -> None:
    rid = log_tool_call(
        conn=tmp_db,
        tool_name="adicionar_tarefa",
        input_json='{"title": null}',
        output_json=None,
        status="error",
        error_msg="title is required",
        duration_ms=5,
        llm_call_id="call_abc123",
    )
    row = tmp_db.execute("SELECT * FROM tool_call_logs WHERE id = ?", (rid,)).fetchone()
    assert row["status"] == "error"
    assert row["error_msg"] == "title is required"
    assert row["llm_call_id"] == "call_abc123"
    assert row["output_json"] is None


def test_log_tool_call_invalid_status_raises(tmp_db: sqlite3.Connection) -> None:
    with pytest.raises(ValueError):
        log_tool_call(
            conn=tmp_db,
            tool_name="x",
            input_json="{}",
            output_json="{}",
            status="weird",  # inválido
            error_msg=None,
            duration_ms=1,
        )
