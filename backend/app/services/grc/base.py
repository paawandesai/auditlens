"""GRC Payload Adapter Protocol and Registry.

Mirrors the ArticleCheck pattern from compliance/base.py.
Each adapter translates an AssessmentResult into a platform-specific
control-level evidence payload.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from app.schemas.compliance import AssessmentResult


@runtime_checkable
class GrcPayloadAdapter(Protocol):
    """Protocol for GRC platform adapters.

    Each implementation translates internal compliance checks
    into platform-specific control payloads.
    """

    def platform_name(self) -> str:
        """Unique identifier for this platform (e.g. 'vanta', 'drata')."""
        ...

    def translate(self, result: AssessmentResult) -> dict:
        """Translate an AssessmentResult into a platform-specific payload."""
        ...

    def control_mapping(self) -> dict[str, str]:
        """Return mapping from our article rule_ids to platform control IDs."""
        ...


class AdapterRegistry:
    """Registry for looking up GRC platform adapters by name."""

    def __init__(self, adapters: Sequence[GrcPayloadAdapter]) -> None:
        self._adapters: dict[str, GrcPayloadAdapter] = {
            a.platform_name(): a for a in adapters
        }

    def get(self, platform: str) -> GrcPayloadAdapter | None:
        """Get adapter by platform name (case-insensitive)."""
        return self._adapters.get(platform.lower())

    def available_platforms(self) -> list[str]:
        """List all registered platform names."""
        return sorted(self._adapters.keys())
