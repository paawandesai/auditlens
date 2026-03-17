"""PDF style constants — colors, fonts, and ParagraphStyle factories.

All visual configuration lives here. No layout logic.
"""

from __future__ import annotations

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.styles import ParagraphStyle

# ---------------------------------------------------------------------------
# Status & severity color palettes
# ---------------------------------------------------------------------------

STATUS_COLORS: dict[str, Color] = {
    "PASS": HexColor("#2eb872"),
    "FAIL": HexColor("#d93636"),
    "PARTIAL": HexColor("#f2a60d"),
}

SEVERITY_COLORS: dict[str, Color] = {
    "critical": HexColor("#d93636"),
    "high": HexColor("#f27a0d"),
    "medium": HexColor("#f2bf0d"),
    "low": HexColor("#888888"),
}

OVERALL_STATUS_COLORS: dict[str, Color] = {
    "COMPLIANT": HexColor("#2eb872"),
    "NON_COMPLIANT": HexColor("#d93636"),
    "PARTIALLY_COMPLIANT": HexColor("#f2a60d"),
}

# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------

TITLE_STYLE = ParagraphStyle(
    "AuditTitle",
    fontSize=22,
    leading=28,
    spaceAfter=6,
    textColor=HexColor("#1a1a2e"),
    fontName="Helvetica-Bold",
)

SUBTITLE_STYLE = ParagraphStyle(
    "AuditSubtitle",
    fontSize=11,
    leading=14,
    spaceAfter=16,
    textColor=HexColor("#555555"),
)

HEADING_STYLE = ParagraphStyle(
    "SectionHeading",
    fontSize=14,
    leading=18,
    spaceBefore=16,
    spaceAfter=8,
    textColor=HexColor("#1a1a2e"),
    fontName="Helvetica-Bold",
)

BODY_STYLE = ParagraphStyle(
    "BodyText",
    fontSize=10,
    leading=13,
    spaceAfter=4,
    textColor=HexColor("#333333"),
)

SMALL_STYLE = ParagraphStyle(
    "SmallText",
    fontSize=8,
    leading=10,
    textColor=HexColor("#888888"),
)

REMEDIATION_STYLE = ParagraphStyle(
    "Remediation",
    fontSize=9,
    leading=12,
    spaceAfter=4,
    textColor=HexColor("#1a1a2e"),
    leftIndent=12,
)
