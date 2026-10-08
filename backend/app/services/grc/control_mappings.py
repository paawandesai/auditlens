"""Static control ID mappings — article rule_ids to platform control IDs.

DEMO MAPPINGS. The Vanta / Drata / Secureframe control IDs below are
illustrative placeholders that show the shape of each platform's payload.
They are NOT real control IDs from those platforms and have not been
validated against their APIs. Every export payload carries
`mapping_disclosure()` so downstream consumers can see this.
"""

from __future__ import annotations

# Platforms whose control IDs in this module are illustrative placeholders.
DEMO_MAPPING_PLATFORMS: frozenset[str] = frozenset({"vanta", "drata", "secureframe"})

_DEMO_NOTICE = (
    "Format demo: control IDs in this export are illustrative placeholders, "
    "not real {platform} control IDs, and the payload has not been validated "
    "against the {platform} API. Map controls manually before importing."
)
_NATIVE_NOTICE = (
    "Control IDs are AuditLens rule IDs (EU_AI_ART_*); no third-party "
    "control mapping is applied."
)


def mapping_disclosure(platform: str) -> dict[str, str]:
    """Return the honesty fields attached to every GRC export payload."""
    name = platform.lower()
    if name in DEMO_MAPPING_PLATFORMS:
        return {
            "mapping_status": "demo",
            "mapping_notice": _DEMO_NOTICE.format(platform=name.capitalize()),
        }
    return {"mapping_status": "native", "mapping_notice": _NATIVE_NOTICE}

# Vanta uses AI-prefixed custom control IDs
VANTA_CONTROL_MAP: dict[str, str] = {
    "EU_AI_ART_5": "AI-PP-001",
    "EU_AI_ART_9": "AI-RM-001",
    "EU_AI_ART_10": "AI-DG-001",
    "EU_AI_ART_11": "AI-TD-001",
    "EU_AI_ART_12": "AI-RK-001",
    "EU_AI_ART_13": "AI-TR-001",
    "EU_AI_ART_14": "AI-HO-001",
    "EU_AI_ART_15": "AI-AR-001",
    "EU_AI_ART_50": "AI-TP-001",
}

# Drata uses CTRL-prefixed IDs
DRATA_CONTROL_MAP: dict[str, str] = {
    "EU_AI_ART_5": "CTRL-AI-008",
    "EU_AI_ART_9": "CTRL-AI-001",
    "EU_AI_ART_10": "CTRL-AI-002",
    "EU_AI_ART_11": "CTRL-AI-003",
    "EU_AI_ART_12": "CTRL-AI-004",
    "EU_AI_ART_13": "CTRL-AI-005",
    "EU_AI_ART_14": "CTRL-AI-006",
    "EU_AI_ART_15": "CTRL-AI-007",
    "EU_AI_ART_50": "CTRL-AI-009",
}

# Secureframe uses SEC-prefixed IDs
SECUREFRAME_CONTROL_MAP: dict[str, str] = {
    "EU_AI_ART_5": "SEC-AI-PP-01",
    "EU_AI_ART_9": "SEC-AI-RM-01",
    "EU_AI_ART_10": "SEC-AI-DG-01",
    "EU_AI_ART_11": "SEC-AI-TD-01",
    "EU_AI_ART_12": "SEC-AI-RK-01",
    "EU_AI_ART_13": "SEC-AI-TR-01",
    "EU_AI_ART_14": "SEC-AI-HO-01",
    "EU_AI_ART_15": "SEC-AI-AR-01",
    "EU_AI_ART_50": "SEC-AI-TP-01",
}

# Generic uses our own rule_ids as-is
GENERIC_CONTROL_MAP: dict[str, str] = {
    "EU_AI_ART_5": "EU_AI_ART_5",
    "EU_AI_ART_9": "EU_AI_ART_9",
    "EU_AI_ART_10": "EU_AI_ART_10",
    "EU_AI_ART_11": "EU_AI_ART_11",
    "EU_AI_ART_12": "EU_AI_ART_12",
    "EU_AI_ART_13": "EU_AI_ART_13",
    "EU_AI_ART_14": "EU_AI_ART_14",
    "EU_AI_ART_15": "EU_AI_ART_15",
    "EU_AI_ART_50": "EU_AI_ART_50",
}
