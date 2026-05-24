"""Testes de src/core/health.py — T-001.13 (cobre R6 da auditoria 001)."""

from __future__ import annotations

import threading
import time

import pytest

from src.core.health import get_health, reset_health_for_tests, set_health


@pytest.fixture(autouse=True)
def _reset_health() -> None:
    reset_health_for_tests()
    yield
    reset_health_for_tests()


def test_get_health_initial_state() -> None:
    h = get_health()
    assert h.status == "UNKNOWN"
    assert h.last_check is None
    assert h.last_error is None


def test_set_health_updates_state() -> None:
    set_health("ONLINE")
    h = get_health()
    assert h.status == "ONLINE"
    assert h.last_check is not None
    assert h.last_error is None


def test_set_health_with_error() -> None:
    set_health("OFFLINE", error="401 unauthorized")
    h = get_health()
    assert h.status == "OFFLINE"
    assert h.last_error == "401 unauthorized"


def test_get_returns_copy_not_reference() -> None:
    set_health("ONLINE")
    h1 = get_health()
    h1.status = "TAMPERED"  # tampering local não afeta estado
    h2 = get_health()
    assert h2.status == "ONLINE"


def test_thread_safety_smoke() -> None:
    """10 threads alternando set/get por 200ms não devem levantar."""
    stop = threading.Event()
    errors: list[Exception] = []

    def writer() -> None:
        try:
            i = 0
            while not stop.is_set():
                set_health("ONLINE" if i % 2 == 0 else "OFFLINE")
                i += 1
        except Exception as e:  # pragma: no cover
            errors.append(e)

    def reader() -> None:
        try:
            while not stop.is_set():
                _ = get_health()
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(5)] + [
        threading.Thread(target=reader) for _ in range(5)
    ]
    for t in threads:
        t.start()
    time.sleep(0.2)
    stop.set()
    for t in threads:
        t.join(timeout=2.0)

    assert not errors, f"erros em threads: {errors}"
