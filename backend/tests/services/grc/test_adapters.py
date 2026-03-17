"""Tests for GRC adapter implementations."""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_09 import Article09Check
from app.services.compliance.article_10 import Article10Check
from app.services.compliance.article_11 import Article11Check
from app.services.compliance.article_12 import Article12Check
from app.services.compliance.article_13 import Article13Check
from app.services.compliance.article_14 import Article14Check
from app.services.compliance.article_15 import Article15Check
from app.services.compliance.base import ComplianceEngine
from app.services.grc.base import AdapterRegistry, GrcPayloadAdapter
from app.services.grc.drata_adapter import DrataAdapter
from app.services.grc.generic_adapter import GenericAdapter
from app.services.grc.secureframe_adapter import SecureframeAdapter
from app.services.grc.vanta_adapter import VantaAdapter

ALL_CHECKS = [
    Article09Check(), Article10Check(), Article11Check(), Article12Check(),
    Article13Check(), Article14Check(), Article15Check(),
]


def _assessment(scanner_output: ScannerOutput):
    return ComplianceEngine(ALL_CHECKS).run(scanner_output)


class TestAdapterProtocol:

    def test_vanta_implements_protocol(self):
        assert isinstance(VantaAdapter(), GrcPayloadAdapter)

    def test_drata_implements_protocol(self):
        assert isinstance(DrataAdapter(), GrcPayloadAdapter)

    def test_secureframe_implements_protocol(self):
        assert isinstance(SecureframeAdapter(), GrcPayloadAdapter)

    def test_generic_implements_protocol(self):
        assert isinstance(GenericAdapter(), GrcPayloadAdapter)


class TestAdapterRegistry:

    def test_available_platforms(self):
        registry = AdapterRegistry([VantaAdapter(), DrataAdapter(), GenericAdapter()])
        platforms = registry.available_platforms()
        assert "vanta" in platforms
        assert "drata" in platforms
        assert "generic" in platforms

    def test_get_existing(self):
        registry = AdapterRegistry([VantaAdapter()])
        adapter = registry.get("vanta")
        assert adapter is not None
        assert adapter.platform_name() == "vanta"

    def test_get_missing(self):
        registry = AdapterRegistry([VantaAdapter()])
        assert registry.get("nonexistent") is None

    def test_case_insensitive(self):
        registry = AdapterRegistry([VantaAdapter()])
        # Platform names are stored lowercase
        assert registry.get("vanta") is not None


class TestVantaAdapter:

    def test_platform_name(self):
        assert VantaAdapter().platform_name() == "vanta"

    def test_translate_non_compliant(self, non_compliant_scanner_output):
        assessment = _assessment(non_compliant_scanner_output)
        result = VantaAdapter().translate(assessment)

        assert result["platform"] == "vanta"
        assert len(result["controls"]) == 7
        # All should be FAILING for non-compliant
        statuses = {c["status"] for c in result["controls"]}
        assert "FAILING" in statuses

    def test_translate_compliant(self, fully_compliant_scanner_output):
        assessment = _assessment(fully_compliant_scanner_output)
        result = VantaAdapter().translate(assessment)

        statuses = {c["status"] for c in result["controls"]}
        assert "PASSING" in statuses

    def test_control_ids_mapped(self, non_compliant_scanner_output):
        assessment = _assessment(non_compliant_scanner_output)
        result = VantaAdapter().translate(assessment)

        control_ids = {c["control_id"] for c in result["controls"]}
        assert "AI-RM-001" in control_ids  # Article 9

    def test_evidence_structure(self, non_compliant_scanner_output):
        assessment = _assessment(non_compliant_scanner_output)
        result = VantaAdapter().translate(assessment)

        control = result["controls"][0]
        assert "evidence" in control
        assert control["evidence"]["source"] == "auditlens"
        assert "collected_at" in control["evidence"]


class TestDrataAdapter:

    def test_platform_name(self):
        assert DrataAdapter().platform_name() == "drata"

    def test_partial_maps_to_failing(self, partial_scanner_output):
        assessment = _assessment(partial_scanner_output)
        result = DrataAdapter().translate(assessment)

        # Drata has no PARTIAL — should map to FAILING
        statuses = {c["status"] for c in result["controls"]}
        assert "PASSING" in statuses or "FAILING" in statuses
        # No AT_RISK or PARTIAL in Drata output
        assert "AT_RISK" not in statuses
        assert "PARTIAL" not in statuses

    def test_control_ids(self, non_compliant_scanner_output):
        assessment = _assessment(non_compliant_scanner_output)
        result = DrataAdapter().translate(assessment)

        control_ids = {c["control_id"] for c in result["controls"]}
        assert "CTRL-AI-001" in control_ids


class TestSecureframeAdapter:

    def test_platform_name(self):
        assert SecureframeAdapter().platform_name() == "secureframe"

    def test_status_mapping(self, partial_scanner_output):
        assessment = _assessment(partial_scanner_output)
        result = SecureframeAdapter().translate(assessment)

        statuses = {c["status"] for c in result["controls"]}
        # Secureframe uses met/not_met/partially_met
        assert statuses.issubset({"met", "not_met", "partially_met"})

    def test_control_ids(self, non_compliant_scanner_output):
        assessment = _assessment(non_compliant_scanner_output)
        result = SecureframeAdapter().translate(assessment)

        control_ids = {c["control_id"] for c in result["controls"]}
        assert "SEC-AI-RM-01" in control_ids


class TestGenericAdapter:

    def test_platform_name(self):
        assert GenericAdapter().platform_name() == "generic"

    def test_includes_summary(self, non_compliant_scanner_output):
        assessment = _assessment(non_compliant_scanner_output)
        result = GenericAdapter().translate(assessment)

        assert "summary" in result
        assert "compliance_score" in result["summary"]
        assert result["summary"]["total_controls"] == 7

    def test_includes_remediation(self, non_compliant_scanner_output):
        assessment = _assessment(non_compliant_scanner_output)
        result = GenericAdapter().translate(assessment)

        # At least some controls should have remediation
        remediations = [c["remediation"] for c in result["controls"] if c["remediation"]]
        assert len(remediations) > 0
