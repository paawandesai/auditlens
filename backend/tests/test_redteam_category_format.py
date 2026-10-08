"""redteam-engine sends snake_case categories; they must route like kebab-case.

Regression: `tool_misuse` findings from a real `redteam push` fell through to
the Article 9 default instead of Article 14 (human oversight), because the
mapper only knew "tool-misuse".
"""

from __future__ import annotations

import pytest

from app.schemas.redteam import RedTeamScanResult
from app.services.redteam_mapper import map_redteam_to_assessment


def _scan(category: str) -> RedTeamScanResult:
    return RedTeamScanResult(
        scan_id="scan-engine-format",
        findings=[{
            "finding_id": "f-1",
            "category": category,
            "severity": 5,
            "grade": "critical_fail",
            "reasoning": "Agent changed the account email without verifying identity.",
        }],
    )


@pytest.mark.parametrize(
    ("engine_category", "article"),
    [
        ("prompt_injection_rag", "Article 9"),
        ("tool_misuse", "Article 14"),
        ("cross_agent_injection", "Article 15"),
        ("memory_poisoning", "Article 12"),
        ("tool-misuse", "Article 14"),
    ],
)
def test_engine_categories_route_to_primary_article(engine_category: str, article: str) -> None:
    assessment = map_redteam_to_assessment(_scan(engine_category))
    assert [c.article for c in assessment.checks] == [article]
    assert assessment.checks[0].status == "FAIL"


def test_category_is_canonicalised() -> None:
    assert _scan(" Tool_Misuse ").findings[0].category == "tool-misuse"
