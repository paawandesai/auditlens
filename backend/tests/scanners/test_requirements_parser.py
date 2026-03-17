"""Tests for RequirementsParser — dependency manifest parsing."""

from __future__ import annotations

import pytest

from app.scanners.requirements_parser import RequirementsParser


@pytest.fixture
def parser() -> RequirementsParser:
    return RequirementsParser()


class TestRequirementsTxt:

    def test_detects_scikit_learn(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "scikit-learn==1.4.0\n"})
        assert len(result) == 1
        assert result[0].name == "scikit-learn"
        assert result[0].version == "==1.4.0"
        assert result[0].hr_relevance_score == 0.7

    def test_detects_multiple_frameworks(self, parser: RequirementsParser):
        content = "scikit-learn==1.4.0\ntensorflow>=2.15.0\npandas\nrequests\n"
        result = parser.parse({"requirements.txt": content})
        names = {f.name for f in result}
        assert "scikit-learn" in names
        assert "tensorflow" in names
        assert "pandas" in names
        assert "requests" not in names  # Not an ML framework

    def test_skips_comments_and_blanks(self, parser: RequirementsParser):
        content = "# ML deps\nscikit-learn\n\n# Utils\nrequests\n"
        result = parser.parse({"requirements.txt": content})
        assert len(result) == 1

    def test_handles_extras(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "scikit-learn[extra]==1.0\n"})
        assert result[0].name == "scikit-learn"

    def test_fairness_high_relevance(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "fairlearn>=0.8\n"})
        assert result[0].hr_relevance_score == 0.95

    def test_empty_file(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": ""})
        assert result == []


class TestPackageJson:

    def test_detects_openai(self, parser: RequirementsParser):
        content = '{"dependencies": {"openai": "^4.0.0"}, "devDependencies": {}}'
        result = parser.parse({"package.json": content})
        assert len(result) == 1
        assert result[0].name == "openai"
        assert result[0].version == "^4.0.0"

    def test_detects_dev_dependencies(self, parser: RequirementsParser):
        content = '{"dependencies": {}, "devDependencies": {"@tensorflow/tfjs": "^4.0"}}'
        result = parser.parse({"package.json": content})
        assert result[0].name == "@tensorflow/tfjs"

    def test_invalid_json(self, parser: RequirementsParser):
        result = parser.parse({"package.json": "not json {"})
        assert result == []

    def test_no_ml_deps(self, parser: RequirementsParser):
        content = '{"dependencies": {"express": "^4.0", "lodash": "^4.0"}}'
        result = parser.parse({"package.json": content})
        assert result == []


class TestPyprojectToml:

    def test_detects_from_dependencies(self, parser: RequirementsParser):
        content = '[project]\ndependencies = [\n    "scikit-learn>=1.4",\n    "pandas",\n]\n'
        result = parser.parse({"pyproject.toml": content})
        names = {f.name for f in result}
        assert "scikit-learn" in names
        assert "pandas" in names

    def test_inline_dependencies(self, parser: RequirementsParser):
        content = '[project]\ndependencies = ["torch>=2.0"]\n'
        result = parser.parse({"pyproject.toml": content})
        assert len(result) == 1
        assert result[0].name == "torch"


class TestPipfile:

    def test_detects_packages(self, parser: RequirementsParser):
        content = (
            "[packages]\n"
            "scikit-learn = \"*\"\n"
            "pandas = \">=1.5\"\n\n"
            "[dev-packages]\n"
            "pytest = \"*\"\n"
        )
        result = parser.parse({"Pipfile": content})
        names = {f.name for f in result}
        assert "scikit-learn" in names
        assert "pandas" in names
        assert "pytest" not in names


class TestMultiManifest:

    def test_deduplicates_across_files(self, parser: RequirementsParser):
        files = {
            "requirements.txt": "scikit-learn==1.4\n",
            "pyproject.toml": '[project]\ndependencies = ["scikit-learn>=1.4"]\n',
        }
        result = parser.parse(files)
        assert len(result) == 1

    def test_combines_different_frameworks(self, parser: RequirementsParser):
        files = {
            "requirements.txt": "scikit-learn\n",
            "package.json": '{"dependencies": {"openai": "^4.0"}}',
        }
        result = parser.parse(files)
        names = {f.name for f in result}
        assert "scikit-learn" in names
        assert "openai" in names
