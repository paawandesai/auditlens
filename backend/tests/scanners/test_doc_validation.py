"""Tests for section-based document validation."""

from __future__ import annotations

from app.scanners.content_analyzer import validate_doc_sections


class TestValidateDocSections:
    """Tests for validate_doc_sections()."""

    def test_unknown_doc_type_returns_none(self):
        result = validate_doc_sections("random_file.md", "some content")
        assert result is None

    def test_risk_assessment_all_sections(self):
        content = """
# Risk Assessment

## Risk Identification
We identified the following risks...

## Risk Estimation
The probability of each risk...

## Risk Evaluation
Based on evaluation criteria...

## Risk Mitigation
Our mitigation strategy...

## Residual Risk
After mitigation, residual risk remains...
"""
        result = validate_doc_sections("risk_assessment.md", content)
        assert result is not None
        assert result.doc_type == "risk_assessment"
        assert result.completeness_score == 1.0
        assert len(result.sections_missing) == 0

    def test_risk_assessment_partial_sections(self):
        content = """
# Risk Assessment

## Risk Identification
Some risks identified.

## Risk Mitigation
Steps to mitigate.
"""
        result = validate_doc_sections("RISK_ASSESSMENT.md", content)
        assert result is not None
        assert result.doc_type == "risk_assessment"
        assert "risk identification" in result.sections_found
        assert "risk mitigation" in result.sections_found
        assert "risk estimation" in result.sections_missing
        assert 0 < result.completeness_score < 1.0

    def test_risk_assessment_empty_doc(self):
        result = validate_doc_sections("risk_assessment.md", "")
        assert result is not None
        assert result.completeness_score == 0.0
        assert len(result.sections_found) == 0
        assert len(result.sections_missing) == 5

    def test_model_card_all_sections(self):
        content = """
# Model Card

## Intended Use
This model is intended for...

## Limitations
Known limitations include...

## Performance
Evaluated on benchmark X with accuracy...

## Training Data
The model was trained on...
"""
        result = validate_doc_sections("model_card.md", content)
        assert result is not None
        assert result.doc_type == "model_card"
        assert result.completeness_score == 1.0

    def test_model_card_partial(self):
        content = "# Model Card\n\n## Intended Use\nFor classification."
        result = validate_doc_sections("model-card.md", content)
        assert result is not None
        assert result.doc_type == "model_card"
        assert result.completeness_score == 0.25  # 1 out of 4

    def test_data_documentation_detected(self):
        content = "Data sources include X. Data quality is measured by Y. Bias analysis done."
        result = validate_doc_sections("data_card.md", content)
        assert result is not None
        assert result.doc_type == "data_documentation"
        assert result.completeness_score == 1.0

    def test_dataset_card_variant(self):
        content = "Data sources documented here."
        result = validate_doc_sections("dataset-card.md", content)
        assert result is not None
        assert result.doc_type == "data_documentation"

    def test_datasheet_variant(self):
        content = "Data quality metrics are tracked."
        result = validate_doc_sections("datasheet.md", content)
        assert result is not None
        assert result.doc_type == "data_documentation"

    def test_human_oversight_doc(self):
        content = "Human oversight ensures intervention is possible. Override allowed."
        result = validate_doc_sections("human_oversight.md", content)
        assert result is not None
        assert result.doc_type == "human_oversight"
        assert result.completeness_score == 1.0

    def test_case_insensitive_matching(self):
        content = "RISK IDENTIFICATION noted. RISK MITIGATION planned."
        result = validate_doc_sections("risk_assessment.md", content)
        assert result is not None
        assert "risk identification" in result.sections_found
        assert "risk mitigation" in result.sections_found

    def test_nested_path_classification(self):
        content = "Intended use and limitations documented. Performance evaluated. Training data described."
        result = validate_doc_sections("docs/model_card.md", content)
        assert result is not None
        assert result.doc_type == "model_card"

    def test_completeness_score_proportional(self):
        """2 out of 5 risk assessment sections = 0.4."""
        content = "risk identification and risk estimation"
        result = validate_doc_sections("risk_assessment.md", content)
        assert result is not None
        assert result.completeness_score == 0.4

    def test_transparency_doc(self):
        content = "System capabilities include X. Limitations are Y. Intended use is Z."
        result = validate_doc_sections("transparency.md", content)
        assert result is not None
        assert result.doc_type == "transparency"
        assert result.completeness_score == 1.0
