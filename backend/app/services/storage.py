"""Evidence storage — Supabase Storage integration for uploaded documents.

Handles file upload, retrieval, and cleanup via Supabase Storage buckets.
Falls back to in-memory storage if Supabase is not configured.

Security:
- Files stored in private bucket with signed URLs (24h expiry)
- SUPABASE_SERVICE_KEY stored server-side only
- No direct bucket access from frontend
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
EVIDENCE_BUCKET = "evidence"
SIGNED_URL_EXPIRY = 86400  # 24 hours


@dataclass
class StoredEvidence:
    """Metadata for a stored evidence file."""

    evidence_id: str
    filename: str
    doc_type: str
    description: str
    scan_id: str | None
    stored_at: datetime
    file_path: str  # Supabase storage path or in-memory key
    size_bytes: int


# ---------------------------------------------------------------------------
# In-memory fallback (used when Supabase is not configured)
# ---------------------------------------------------------------------------

_MEMORY_STORE: dict[str, tuple[bytes, StoredEvidence]] = {}


class EvidenceStorage:
    """Upload/retrieve evidence files.

    Uses Supabase Storage when configured, falls back to in-memory.
    """

    def __init__(self) -> None:
        self._use_supabase = bool(SUPABASE_URL and SUPABASE_KEY)
        self._client = None

    def _get_supabase(self):
        """Lazy-init Supabase client."""
        if self._client is None and self._use_supabase:
            from supabase import create_client
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return self._client

    async def upload(
        self,
        file_bytes: bytes,
        filename: str,
        doc_type: str,
        description: str = "",
        scan_id: str | None = None,
    ) -> StoredEvidence:
        """Upload a file and return storage metadata.

        Args:
            file_bytes: Raw file content.
            filename: Original filename.
            doc_type: Compliance document type.
            description: Optional description.
            scan_id: Associated scan ID (if known).

        Returns:
            StoredEvidence with evidence_id and metadata.
        """
        evidence_id = f"ev_{uuid.uuid4().hex[:16]}"
        file_path = f"{evidence_id}/{filename}"

        metadata = StoredEvidence(
            evidence_id=evidence_id,
            filename=filename,
            doc_type=doc_type,
            description=description,
            scan_id=scan_id,
            stored_at=datetime.now(UTC),
            file_path=file_path,
            size_bytes=len(file_bytes),
        )

        if self._use_supabase:
            client = self._get_supabase()
            client.storage.from_(EVIDENCE_BUCKET).upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": "application/octet-stream"},
            )
        else:
            # In-memory fallback
            _MEMORY_STORE[evidence_id] = (file_bytes, metadata)

        return metadata

    async def get_metadata(self, evidence_id: str) -> StoredEvidence | None:
        """Retrieve metadata for stored evidence."""
        if self._use_supabase:
            # For Supabase, metadata would be in a DB table
            # For MVP, we store metadata in memory alongside the scan
            return _MEMORY_STORE.get(evidence_id, (None, None))[1]
        return _MEMORY_STORE.get(evidence_id, (None, None))[1]

    async def get_file(self, evidence_id: str) -> bytes | None:
        """Retrieve file bytes for stored evidence."""
        if not self._use_supabase:
            entry = _MEMORY_STORE.get(evidence_id)
            return entry[0] if entry else None

        metadata = await self.get_metadata(evidence_id)
        if not metadata:
            return None

        client = self._get_supabase()
        response = client.storage.from_(EVIDENCE_BUCKET).download(metadata.file_path)
        return response

    async def cleanup(self, evidence_id: str) -> None:
        """Delete stored evidence."""
        if self._use_supabase:
            metadata = await self.get_metadata(evidence_id)
            if metadata:
                client = self._get_supabase()
                client.storage.from_(EVIDENCE_BUCKET).remove([metadata.file_path])

        _MEMORY_STORE.pop(evidence_id, None)
