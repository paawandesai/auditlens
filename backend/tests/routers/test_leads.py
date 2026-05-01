"""Tests for the lead-capture endpoint at POST /api/v1/leads."""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_store(monkeypatch):
    """Spin up a fresh app with an isolated SQLite file for each test.

    The leads endpoint writes to the singleton store created in `lifespan`;
    `TestClient(app)` only triggers lifespan inside `with` blocks, so we yield
    the client from a `with` to ensure init_store has run.
    """
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "test_leads.db")
    monkeypatch.setenv("AUDITLENS_DB_PATH", db_path)

    # Import after env is set so the singleton resolves the override.
    from app.main import app
    from app.storage import sqlite_store

    # Reset module-level singleton between tests.
    sqlite_store._store = None

    with TestClient(app) as client:
        yield client, db_path

    sqlite_store._store = None


def test_capture_lead_persists_email(client_with_store):
    client, db_path = client_with_store
    res = client.post(
        "/api/v1/leads",
        json={"email": "founder@example.com", "scan_context": "github.com/org/repo"},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT email, scan_context FROM leads ORDER BY id DESC LIMIT 1"
    ).fetchall()
    conn.close()
    assert rows == [("founder@example.com", "github.com/org/repo")]


def test_capture_lead_normalises_email(client_with_store):
    client, db_path = client_with_store
    res = client.post(
        "/api/v1/leads",
        json={"email": "  Founder@Example.COM  ", "scan_context": ""},
    )
    assert res.status_code == 200

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT email FROM leads").fetchall()
    conn.close()
    assert rows == [("founder@example.com",)]


def test_capture_lead_rejects_invalid_email(client_with_store):
    client, _ = client_with_store
    res = client.post("/api/v1/leads", json={"email": "not-an-email"})
    assert res.status_code == 422
