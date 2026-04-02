"""SQLite persistence for scan results."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ScanStore:
    """Thin SQLite wrapper for persisting scan and red-team results."""

    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self) -> None:
        """Create tables if they don't exist and enable WAL mode."""
        self._conn.execute("PRAGMA journal_mode=WAL")
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    repo_url TEXT,
                    result_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS redteam_scans (
                    id TEXT PRIMARY KEY,
                    result_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save_scan(self, scan_id: str, repo_url: str, result: dict) -> None:
        """Persist a scan result as a JSON blob."""
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO scans (id, repo_url, result_json, created_at) VALUES (?, ?, ?, ?)",
                (scan_id, repo_url, json.dumps(result), datetime.now(timezone.utc).isoformat()),
            )

    def save_redteam_scan(self, scan_id: str, result: dict) -> None:
        """Persist a red-team scan result as a JSON blob."""
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO redteam_scans (id, result_json, created_at) VALUES (?, ?, ?)",
                (scan_id, json.dumps(result), datetime.now(timezone.utc).isoformat()),
            )

    def get_scan(self, scan_id: str) -> dict | None:
        """Retrieve a scan by ID, checking both tables."""
        row = self._conn.execute(
            "SELECT result_json FROM scans WHERE id = ?", (scan_id,)
        ).fetchone()
        if row:
            return json.loads(row["result_json"])
        row = self._conn.execute(
            "SELECT result_json FROM redteam_scans WHERE id = ?", (scan_id,)
        ).fetchone()
        if row:
            return json.loads(row["result_json"])
        return None

    def get_recent_scans(self, limit: int = 20) -> list[dict]:
        """Return lightweight metadata for recent scans (newest first)."""
        rows = self._conn.execute(
            "SELECT id, repo_url, created_at,"
            " json_extract(result_json, '$.assessment.summary.overall_status') AS status"
            " FROM scans ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "scan_id": r["id"],
                "repo_url": r["repo_url"],
                "created_at": r["created_at"],
                "status": r["status"],
            }
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_store: ScanStore | None = None


def init_store() -> ScanStore:
    """Create the singleton ScanStore. Called once at app startup."""
    global _store  # noqa: PLW0603
    db_path_override = os.environ.get("AUDITLENS_DB_PATH")
    if db_path_override:
        db_path = Path(db_path_override)
    else:
        db_path = Path(__file__).resolve().parent.parent.parent / "data" / "auditlens.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _store = ScanStore(db_path)
    return _store


def get_store() -> ScanStore | None:
    """Return the singleton (None if init_store() has not been called)."""
    return _store
