"""Static control ID mappings — article rule_ids to platform control IDs.

These are placeholder mappings. Actual control IDs will be updated
after researching Vanta/Drata/Secureframe APIs (Week 2, Priority 7).
"""

from __future__ import annotations

# Vanta uses AI-prefixed custom control IDs
VANTA_CONTROL_MAP: dict[str, str] = {
    "EU_AI_ART_9": "AI-RM-001",
    "EU_AI_ART_10": "AI-DG-001",
    "EU_AI_ART_11": "AI-TD-001",
    "EU_AI_ART_12": "AI-RK-001",
    "EU_AI_ART_13": "AI-TR-001",
    "EU_AI_ART_14": "AI-HO-001",
    "EU_AI_ART_15": "AI-AR-001",
}

# Drata uses CTRL-prefixed IDs
DRATA_CONTROL_MAP: dict[str, str] = {
    "EU_AI_ART_9": "CTRL-AI-001",
    "EU_AI_ART_10": "CTRL-AI-002",
    "EU_AI_ART_11": "CTRL-AI-003",
    "EU_AI_ART_12": "CTRL-AI-004",
    "EU_AI_ART_13": "CTRL-AI-005",
    "EU_AI_ART_14": "CTRL-AI-006",
    "EU_AI_ART_15": "CTRL-AI-007",
}

# Secureframe uses SEC-prefixed IDs
SECUREFRAME_CONTROL_MAP: dict[str, str] = {
    "EU_AI_ART_9": "SEC-AI-RM-01",
    "EU_AI_ART_10": "SEC-AI-DG-01",
    "EU_AI_ART_11": "SEC-AI-TD-01",
    "EU_AI_ART_12": "SEC-AI-RK-01",
    "EU_AI_ART_13": "SEC-AI-TR-01",
    "EU_AI_ART_14": "SEC-AI-HO-01",
    "EU_AI_ART_15": "SEC-AI-AR-01",
}

# Generic uses our own rule_ids as-is
GENERIC_CONTROL_MAP: dict[str, str] = {
    "EU_AI_ART_9": "EU_AI_ART_9",
    "EU_AI_ART_10": "EU_AI_ART_10",
    "EU_AI_ART_11": "EU_AI_ART_11",
    "EU_AI_ART_12": "EU_AI_ART_12",
    "EU_AI_ART_13": "EU_AI_ART_13",
    "EU_AI_ART_14": "EU_AI_ART_14",
    "EU_AI_ART_15": "EU_AI_ART_15",
}
