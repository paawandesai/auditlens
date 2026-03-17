"""Tests for RequirementsParser — dependency manifest parsing."""

from __future__ import annotations

import json

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


class TestSetupPy:

    def test_detects_torch(self, parser: RequirementsParser):
        content = (
            "from setuptools import setup\n"
            "setup(\n"
            "    name='my-model',\n"
            "    install_requires=[\n"
            "        'torch>=2.0',\n"
            "        'transformers',\n"
            "        'requests',\n"
            "    ],\n"
            ")\n"
        )
        result = parser.parse({"setup.py": content})
        names = {f.name for f in result}
        assert "torch" in names
        assert "transformers" in names
        assert "requests" not in names

    def test_inline_install_requires(self, parser: RequirementsParser):
        content = 'setup(install_requires=["scikit-learn", "pandas"])'
        result = parser.parse({"setup.py": content})
        names = {f.name for f in result}
        assert "scikit-learn" in names
        assert "pandas" in names

    def test_empty_install_requires(self, parser: RequirementsParser):
        content = "setup(install_requires=[])"
        result = parser.parse({"setup.py": content})
        assert result == []

    def test_no_install_requires(self, parser: RequirementsParser):
        content = "setup(name='foo')"
        result = parser.parse({"setup.py": content})
        assert result == []

    def test_nested_path_setup_py(self, parser: RequirementsParser):
        content = 'setup(install_requires=["torch"])'
        result = parser.parse({"model/setup.py": content})
        names = {f.name for f in result}
        assert "torch" in names


class TestEnvironmentYml:

    def test_detects_conda_deps(self, parser: RequirementsParser):
        content = (
            "name: ml-env\n"
            "dependencies:\n"
            "  - numpy=1.21\n"
            "  - scikit-learn=1.4\n"
        )
        result = parser.parse({"environment.yml": content})
        names = {f.name for f in result}
        assert "numpy" in names
        assert "scikit-learn" in names

    def test_detects_pip_deps(self, parser: RequirementsParser):
        content = (
            "name: ml-env\n"
            "dependencies:\n"
            "  - python=3.11\n"
            "  - pip:\n"
            "    - torch>=2.0\n"
            "    - transformers\n"
        )
        result = parser.parse({"environment.yml": content})
        names = {f.name for f in result}
        assert "torch" in names
        assert "transformers" in names

    def test_empty_dependencies(self, parser: RequirementsParser):
        content = "name: empty\ndependencies:\nchannels:\n  - defaults\n"
        result = parser.parse({"environment.yml": content})
        assert result == []


class TestNewFrameworkSignatures:

    def test_cohere(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "cohere\n"})
        assert len(result) == 1
        assert result[0].name == "cohere"

    def test_face_recognition_high_hr(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "face-recognition\n"})
        assert result[0].hr_relevance_score == 0.95

    def test_deepface(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "deepface\n"})
        assert result[0].name == "deepface"
        assert result[0].hr_relevance_score == 0.95

    def test_google_generativeai(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "google-generativeai\n"})
        assert result[0].name == "google-generativeai"

    def test_js_vercel_ai(self, parser: RequirementsParser):
        content = '{"dependencies": {"@vercel/ai": "^3.0"}}'
        result = parser.parse({"package.json": content})
        assert result[0].name == "@vercel/ai"

    def test_js_google_genai(self, parser: RequirementsParser):
        content = '{"dependencies": {"@google/generative-ai": "^0.1"}}'
        result = parser.parse({"package.json": content})
        assert result[0].name == "@google/generative-ai"

    def test_jax_ecosystem(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "jax>=0.4.0\njaxlib\nflax"})
        names = {fw.name for fw in result}
        assert "jax" in names
        assert "jaxlib" in names
        assert "flax" in names

    def test_huggingface_hub(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "huggingface-hub>=0.20"})
        assert result[0].name == "huggingface-hub"
        assert result[0].hr_relevance_score == 0.4

    def test_tensorflow_gpu_alias(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "tensorflow-gpu==2.15"})
        assert result[0].name == "tensorflow-gpu"
        assert result[0].confidence == 0.95

    def test_langchain_ecosystem(self, parser: RequirementsParser):
        content = "langchain-community\nlangchain-openai\nlangchain-anthropic"
        result = parser.parse({"requirements.txt": content})
        names = {fw.name for fw in result}
        assert names == {"langchain-community", "langchain-openai", "langchain-anthropic"}

    def test_face_recognition_underscore(self, parser: RequirementsParser):
        result = parser.parse({"requirements.txt": "face_recognition"})
        assert result[0].hr_relevance_score == 0.95

    def test_js_azure_openai(self, parser: RequirementsParser):
        pkg = json.dumps({"dependencies": {"@azure/openai": "^1.0"}})
        result = parser.parse({"package.json": pkg})
        assert result[0].name == "@azure/openai"

    def test_js_ai_sdk_providers(self, parser: RequirementsParser):
        pkg = json.dumps({"dependencies": {
            "@ai-sdk/openai": "^1.0",
            "@ai-sdk/anthropic": "^1.0",
        }})
        result = parser.parse({"package.json": pkg})
        names = {fw.name for fw in result}
        assert "@ai-sdk/openai" in names
        assert "@ai-sdk/anthropic" in names

    def test_js_huggingface_packages(self, parser: RequirementsParser):
        pkg = json.dumps({"dependencies": {
            "@huggingface/transformers": "^3.0",
            "@huggingface/inference": "^2.0",
        }})
        result = parser.parse({"package.json": pkg})
        names = {fw.name for fw in result}
        assert "@huggingface/transformers" in names
        assert "@huggingface/inference" in names


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
