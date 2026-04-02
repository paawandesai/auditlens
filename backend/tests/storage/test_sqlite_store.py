"""Tests for SQLite scan persistence."""

from __future__ import annotations

import time

import pytest

from app.storage.sqlite_store import ScanStore


@pytest.fixture()
def store(tmp_path):
    """Create a ScanStore backed by a temp file."""
    return ScanStore(tmp_path / "test.db")


SAMPLE_RESULT = {
    "repository": "https://github.com/org/repo",
    "branch": "main",
    "scanner_output": {"has_model_card": True},
    "assessment": {"assessment_id": "abc-123", "checks": []},
}


class TestInitDb:
    def test_creates_tables(self, store):
        tables = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [t["name"] for t in tables]
        assert "scans" in names
        assert "redteam_scans" in names

    def test_wal_mode_enabled(self, store):
        mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"


class TestSaveAndGetScan:
    def test_round_trip(self, store):
        store.save_scan("scan-1", "https://github.com/org/repo", SAMPLE_RESULT)
        result = store.get_scan("scan-1")
        assert result == SAMPLE_RESULT

    def test_not_found_returns_none(self, store):
        assert store.get_scan("nonexistent") is None

    def test_idempotent_replace(self, store):
        store.save_scan("scan-1", "https://github.com/org/repo", {"v": 1})
        store.save_scan("scan-1", "https://github.com/org/repo", {"v": 2})
        result = store.get_scan("scan-1")
        assert result == {"v": 2}


class TestSaveRedteamScan:
    def test_round_trip(self, store):
        rt_result = {"findings": [{"category": "prompt-injection"}]}
        store.save_redteam_scan("rt-1", rt_result)
        result = store.get_scan("rt-1")
        assert result == rt_result

    def test_not_found_in_other_table(self, store):
        store.save_scan("scan-1", "https://example.com", SAMPLE_RESULT)
        # get_scan checks both tables — scan-1 should be found
        assert store.get_scan("scan-1") is not None


class TestGetRecentScans:
    def test_ordering_newest_first(self, store):
        for i in range(3):
            store.save_scan(f"scan-{i}", f"https://repo-{i}.com", {"i": i})
            time.sleep(0.01)  # ensure distinct timestamps
        recent = store.get_recent_scans(limit=10)
        assert len(recent) == 3
        assert recent[0]["scan_id"] == "scan-2"
        assert recent[-1]["scan_id"] == "scan-0"

    def test_respects_limit(self, store):
        for i in range(5):
            store.save_scan(f"scan-{i}", f"https://repo-{i}.com", {"i": i})
        recent = store.get_recent_scans(limit=2)
        assert len(recent) == 2

    def test_empty_store(self, store):
        assert store.get_recent_scans() == []

    def test_returns_metadata_not_full_result(self, store):
        store.save_scan("scan-1", "https://example.com", SAMPLE_RESULT)
        recent = store.get_recent_scans()
        item = recent[0]
        assert "scan_id" in item
        assert "repo_url" in item
        assert "created_at" in item
        assert "status" in item
        assert "result_json" not in item

    def test_status_extracted_via_json(self, store):
        result_with_status = {
            **SAMPLE_RESULT,
            "assessment": {
                "assessment_id": "abc-123",
                "checks": [],
                "summary": {"overall_status": "PARTIALLY_COMPLIANT"},
            },
        }
        store.save_scan("scan-2", "https://example.com", result_with_status)
        recent = store.get_recent_scans()
        assert recent[0]["status"] == "PARTIALLY_COMPLIANT"

    def test_status_none_when_missing(self, store):
        store.save_scan("scan-3", "https://example.com", SAMPLE_RESULT)
        recent = store.get_recent_scans()
        assert recent[0]["status"] is None
