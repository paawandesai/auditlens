"""Tests for the role-based applicability gate and engine integration."""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck
from app.schemas.scanner import ScannerOutput
from app.services.compliance.applicability import (
    applicable_articles_for_role,
    is_applicable,
    non_applicable_articles_for_role,
    normalise_role,
)
from app.services.compliance.base import ComplianceEngine

# ---------------------------------------------------------------------------
# Pure applicability function
# ---------------------------------------------------------------------------


class TestNormaliseRole:
    def test_known_role_passes_through(self) -> None:
        assert normalise_role("provider") == "provider"
        assert normalise_role("library") == "library"

    def test_unknown_role_becomes_undeclared(self) -> None:
        assert normalise_role("ceo") == "undeclared"
        assert normalise_role("") == "undeclared"
        assert normalise_role(None) == "undeclared"

    def test_case_and_whitespace_normalised(self) -> None:
        assert normalise_role("  Provider ") == "provider"
        assert normalise_role("LIBRARY") == "library"


class TestIsApplicable:
    def test_universal_articles_apply_to_all_roles(self) -> None:
        for role in ("provider", "deployer", "both", "library", "tool", "gpai"):
            assert is_applicable("Article 5", role) is True
            assert is_applicable("Article 6", role) is True

    def test_provider_articles_skip_for_deployer(self) -> None:
        assert is_applicable("Article 9", "deployer") is False
        assert is_applicable("Article 16", "deployer") is False

    def test_deployer_articles_skip_for_provider(self) -> None:
        assert is_applicable("Article 26", "provider") is False
        assert is_applicable("Article 27", "provider") is False

    def test_both_role_gets_provider_and_deployer_articles(self) -> None:
        assert is_applicable("Article 9", "both") is True
        assert is_applicable("Article 26", "both") is True

    def test_library_only_gets_universal(self) -> None:
        assert is_applicable("Article 5", "library") is True
        assert is_applicable("Article 6", "library") is True
        for art in ("Article 9", "Article 16", "Article 26", "Article 27", "Article 53"):
            assert is_applicable(art, "library") is False

    def test_tool_only_gets_universal(self) -> None:
        assert is_applicable("Article 5", "tool") is True
        assert is_applicable("Article 26", "tool") is False

    def test_gpai_systemic_gets_systemic_risk_only(self) -> None:
        assert is_applicable("Article 55", "gpai_systemic") is True
        assert is_applicable("Article 55", "gpai") is False
        assert is_applicable("Article 55", "provider") is False

    def test_undeclared_runs_universal_and_provider_articles(self) -> None:
        for art in ("Article 5", "Article 6", "Article 9", "Article 16",
                    "Article 50", "Article 72"):
            assert is_applicable(art, "undeclared") is True

    def test_undeclared_skips_deployer_and_gpai_only_articles(self) -> None:
        for art in ("Article 26", "Article 27", "Article 53", "Article 55"):
            assert is_applicable(art, "undeclared") is False

    def test_undeclared_runs_unknown_articles(self) -> None:
        assert is_applicable("Article 99", "undeclared") is True


class TestArticleListsByRole:
    def test_library_returns_only_universal(self) -> None:
        assert applicable_articles_for_role("library") == ["Article 5", "Article 6"]

    def test_provider_excludes_deployer_only(self) -> None:
        applicable = applicable_articles_for_role("provider")
        assert "Article 26" not in applicable
        assert "Article 27" not in applicable
        assert "Article 9" in applicable

    def test_non_applicable_complements_applicable(self) -> None:
        for role in ("provider", "deployer", "library", "gpai"):
            applicable = set(applicable_articles_for_role(role))
            non_applicable = set(non_applicable_articles_for_role(role))
            assert applicable.isdisjoint(non_applicable)


# ---------------------------------------------------------------------------
# Engine integration
# ---------------------------------------------------------------------------


class _FakeCheck:
    """Minimal ArticleCheck stub that always FAILs (critical)."""

    def __init__(self, article: str, rule_id: str = "RULE") -> None:
        self.article = article
        self.rule_id = rule_id
        self.rule_name = f"Test {article}"
        self.severity = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status="FAIL",
            severity=self.severity,
            evidence=CheckEvidence(description="forced fail", source="test"),
            details={"forced": True},
        )


class TestEngineApplicability:
    def test_library_role_marks_provider_articles_na(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([
            _FakeCheck("Article 5", "ART_5"),
            _FakeCheck("Article 9", "ART_9"),
            _FakeCheck("Article 27", "ART_27"),
        ])
        result = engine.run(minimal_scanner_output, role="library")

        by_article = {c.article: c for c in result.checks}
        assert by_article["Article 5"].status == "FAIL"
        assert by_article["Article 5"].is_applicable is True
        assert by_article["Article 9"].status == "N/A"
        assert by_article["Article 9"].is_applicable is False
        assert by_article["Article 27"].status == "N/A"

    def test_score_excludes_na_checks(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([
            _FakeCheck("Article 5", "ART_5"),    # universal — runs (FAIL)
            _FakeCheck("Article 9", "ART_9"),    # not applicable for library
            _FakeCheck("Article 27", "ART_27"),  # not applicable for library
        ])
        result = engine.run(minimal_scanner_output, role="library")
        # Only Art. 5 is applicable; it FAILs critical → score 0
        assert result.summary.total_checks == 1
        assert result.summary.failed == 1
        assert result.summary.compliance_score == 0
        # Critical_failures only contains the applicable failure
        assert result.summary.critical_failures == ["ART_5"]

    def test_critical_failures_drop_na_articles(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        # Without role gating, Art. 27 FAIL would be in critical_failures.
        # With role=library it must not be.
        engine = ComplianceEngine([_FakeCheck("Article 27", "ART_27")])
        result = engine.run(minimal_scanner_output, role="library")
        assert "ART_27" not in result.summary.critical_failures

    def test_undeclared_scores_provider_articles_and_marks_role_declared_false(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([_FakeCheck("Article 9", "ART_9")])
        result = engine.run(minimal_scanner_output)  # default role
        assert result.role == "undeclared"
        assert result.role_declared is False
        assert result.checks[0].status == "FAIL"
        assert result.checks[0].is_applicable is True

    def test_undeclared_does_not_score_fria(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([_FakeCheck("Article 27", "ART_27")])
        result = engine.run(minimal_scanner_output)  # default role
        fria = result.checks[0]
        assert fria.status == "N/A"
        assert fria.is_applicable is False
        assert "no role declared" in fria.evidence.description.lower()
        assert "ART_27" not in result.summary.critical_failures
        assert result.summary.total_checks == 0

    def test_provider_role_sets_role_declared_true(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([_FakeCheck("Article 9", "ART_9")])
        result = engine.run(minimal_scanner_output, role="provider")
        assert result.role == "provider"
        assert result.role_declared is True

    def test_sme_flag_persists_to_assessment(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([])
        result = engine.run(minimal_scanner_output, role="provider", sme=True)
        assert result.sme is True
