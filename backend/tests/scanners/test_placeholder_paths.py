"""Empty / stub compliance docs must not satisfy Art. 9 or Art. 11 sub-checks."""

from __future__ import annotations

from app.scanners.github_scanner import MIN_PLACEHOLDER_CHARS, _detect_placeholder_paths
from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_09 import Article09Check
from app.services.compliance.article_11 import Article11Check

STUB = "# Risk Assessment\n\nTBD\n"
REAL = "# Risk Assessment\n\n" + "Known risk: prompt injection via retrieved docs. " * 10


def _sub(check, sub_id: str) -> bool:
    return next(s.passed for s in check.sub_checks if s.id == sub_id)


def test_detects_short_matched_files_only() -> None:
    contents = {"RISK_ASSESSMENT.md": STUB, "MODEL_CARD.md": REAL, "README.md": "hi"}
    matched = {"has_risk_assessment": ["RISK_ASSESSMENT.md"], "has_model_card": ["MODEL_CARD.md"]}
    assert len(STUB.strip()) < MIN_PLACEHOLDER_CHARS
    # README.md is short but matched no signal, so it is not reported.
    assert _detect_placeholder_paths(contents, matched) == ["RISK_ASSESSMENT.md"]


def test_unfetched_matches_are_not_classified() -> None:
    matched = {"has_risk_assessment": ["docs/risk.md"]}
    assert _detect_placeholder_paths({}, matched) == []


def test_article_09_rejects_placeholder_risk_assessment() -> None:
    output = ScannerOutput(
        repo_url="https://github.com/acme/stub",
        has_risk_assessment=True,
        matched_paths={"has_risk_assessment": ["RISK_ASSESSMENT.md"]},
        placeholder_paths=["RISK_ASSESSMENT.md"],
    )
    assert _sub(Article09Check().evaluate(output), "risk_assessment_exists") is False


def test_article_09_accepts_real_file_alongside_placeholder() -> None:
    output = ScannerOutput(
        repo_url="https://github.com/acme/mixed",
        has_risk_assessment=True,
        matched_paths={"has_risk_assessment": ["RISK_ASSESSMENT.md", "docs/risk.md"]},
        placeholder_paths=["RISK_ASSESSMENT.md"],
    )
    assert _sub(Article09Check().evaluate(output), "risk_assessment_exists") is True


def test_article_11_rejects_placeholder_model_card() -> None:
    output = ScannerOutput(
        repo_url="https://github.com/acme/stub",
        has_model_card=True,
        matched_paths={"has_model_card": ["MODEL_CARD.md"]},
        placeholder_paths=["MODEL_CARD.md"],
    )
    assert _sub(Article11Check().evaluate(output), "model_card_exists") is False
