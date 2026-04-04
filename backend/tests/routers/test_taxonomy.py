"""Tests for taxonomy endpoints — EU AI Act articles and jurisdiction coverage."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def api_client():
    return TestClient(app)


class TestEuAiActTaxonomy:

    def test_returns_all_articles(self, api_client):
        response = api_client.get("/api/v1/taxonomy/eu-ai-act")
        assert response.status_code == 200
        data = response.json()
        assert data["framework"] == "EU AI Act"
        assert len(data["articles"]) >= 15

    def test_automated_articles_present(self, api_client):
        response = api_client.get("/api/v1/taxonomy/eu-ai-act")
        data = response.json()
        automated = [a for a in data["articles"] if a["check_type"] == "automated"]
        assert len(automated) >= 9, f"Expected 9+ automated articles, got {len(automated)}"

    def test_article_5_is_critical(self, api_client):
        response = api_client.get("/api/v1/taxonomy/eu-ai-act")
        data = response.json()
        art5 = next(a for a in data["articles"] if a["article"] == "Article 5")
        assert art5["severity"] == "critical"
        assert art5["coverage"] == "full"
        assert art5["risk_tier"] == "all"

    def test_planned_articles_have_requirements(self, api_client):
        response = api_client.get("/api/v1/taxonomy/eu-ai-act")
        data = response.json()
        planned = [a for a in data["articles"] if a["coverage"] == "planned"]
        for article in planned:
            assert len(article["requirements"]) > 0, (
                f"{article['article']} is planned but has no requirements"
            )

    def test_summary_statistics(self, api_client):
        response = api_client.get("/api/v1/taxonomy/eu-ai-act")
        data = response.json()
        summary = data["summary"]
        assert summary["total_articles"] >= 15
        assert summary["automated"] >= 9
        assert summary["coverage"]["requirements_covered"] > 0
        assert summary["coverage"]["percentage"] > 0

    def test_each_article_has_enforcement_date(self, api_client):
        response = api_client.get("/api/v1/taxonomy/eu-ai-act")
        data = response.json()
        for article in data["articles"]:
            assert article["enforcement_date"], (
                f"{article['article']} missing enforcement_date"
            )

    def test_requirements_have_scanner_field_mapping(self, api_client):
        """Automated requirements with direct scanner mapping should have fields."""
        response = api_client.get("/api/v1/taxonomy/eu-ai-act")
        data = response.json()
        for article in data["articles"]:
            for req in article["requirements"]:
                if req["covered"] and req["check_type"] == "automated":
                    assert len(req["scanner_fields"]) > 0, (
                        f"{req['requirement_id']} is automated+covered but maps to no scanner fields"
                    )


class TestJurisdictions:

    def test_returns_jurisdictions(self, api_client):
        response = api_client.get("/api/v1/taxonomy/jurisdictions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jurisdictions"]) >= 10

    def test_eu_ai_act_is_supported(self, api_client):
        response = api_client.get("/api/v1/taxonomy/jurisdictions")
        data = response.json()
        eu = next(j for j in data["jurisdictions"] if j["law_id"] == "eu_ai_act")
        assert eu["coverage_status"] == "supported"
        assert eu["scanner_coverage_pct"] >= 80

    def test_colorado_is_coming_soon(self, api_client):
        response = api_client.get("/api/v1/taxonomy/jurisdictions")
        data = response.json()
        co = next(j for j in data["jurisdictions"] if j["law_id"] == "colorado_sb24_205")
        assert co["coverage_status"] == "coming_soon"
        assert co["law_status"] == "active"

    def test_nyc_ll144_is_coming_soon(self, api_client):
        response = api_client.get("/api/v1/taxonomy/jurisdictions")
        data = response.json()
        nyc = next(j for j in data["jurisdictions"] if j["law_id"] == "nyc_ll144")
        assert nyc["coverage_status"] == "coming_soon"
        assert "employment" in nyc["sectors"]

    def test_each_jurisdiction_has_overlaps(self, api_client):
        response = api_client.get("/api/v1/taxonomy/jurisdictions")
        data = response.json()
        for j in data["jurisdictions"]:
            assert len(j["requirement_overlaps"]) > 0, (
                f"{j['short_name']} has no requirement overlaps"
            )

    def test_summary_counts(self, api_client):
        response = api_client.get("/api/v1/taxonomy/jurisdictions")
        data = response.json()
        summary = data["summary"]
        assert summary["supported"] >= 1
        assert summary["coming_soon"] >= 5
        assert summary["total_jurisdictions"] == len(data["jurisdictions"])


class TestTaxonomySummary:

    def test_returns_overview(self, api_client):
        response = api_client.get("/api/v1/taxonomy/summary")
        assert response.status_code == 200
        data = response.json()
        assert "eu_ai_act" in data
        assert "jurisdictions" in data
        assert "compliance_frameworks" in data

    def test_framework_list_complete(self, api_client):
        response = api_client.get("/api/v1/taxonomy/summary")
        data = response.json()
        frameworks = data["compliance_frameworks"]
        ids = {f["id"] for f in frameworks}
        assert "eu_ai_act" in ids
        assert "colorado_sb24_205" in ids
        assert "nyc_ll144" in ids
        assert "iso_42001" in ids

    def test_supported_framework_exists(self, api_client):
        response = api_client.get("/api/v1/taxonomy/summary")
        data = response.json()
        supported = [f for f in data["compliance_frameworks"] if f["status"] == "supported"]
        assert len(supported) >= 1
