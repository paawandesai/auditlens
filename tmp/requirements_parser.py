"""Pass 1: Dependency Detection Scanner.

Parses dependency manifests (requirements.txt, package.json, pyproject.toml, Pipfile)
to detect ML/AI frameworks. Each framework has a pre-scored HR relevance weight
used downstream by the risk classifier.

This is the first pass in the three-pass scanning pipeline.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum


class Ecosystem(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GO = "go"


@dataclass
class DetectedFramework:
    """A detected ML/AI framework with metadata for risk classification."""

    name: str
    version: str | None = None
    ecosystem: Ecosystem = Ecosystem.PYTHON
    category: str = "ml_general"
    hr_relevance_score: float = 0.0  # 0.0 - 1.0, how likely used in HR/employment
    description: str = ""
    is_ai_framework: bool = True


# ---------------------------------------------------------------------------
# Framework Signature Database
# ---------------------------------------------------------------------------
# Each entry maps a package name to its classification metadata.
# hr_relevance_score indicates likelihood of HR/employment use case:
#   0.9+ = Very commonly used in hiring/HR (e.g., resume parsers)
#   0.5-0.8 = General ML that COULD be used in HR
#   0.1-0.4 = Unlikely HR use but still AI/ML
#   0.0 = Not AI/ML related

PYTHON_FRAMEWORK_SIGNATURES: dict[str, dict] = {
    # --- Core ML Frameworks ---
    "scikit-learn": {
        "category": "ml_classical",
        "hr_relevance": 0.7,
        "description": "Classical ML algorithms — commonly used for candidate scoring, classification",
    },
    "sklearn": {
        "category": "ml_classical",
        "hr_relevance": 0.7,
        "description": "scikit-learn alias",
    },
    "tensorflow": {
        "category": "ml_deep_learning",
        "hr_relevance": 0.5,
        "description": "Deep learning framework — used in NLP for resume parsing, candidate matching",
    },
    "torch": {
        "category": "ml_deep_learning",
        "hr_relevance": 0.5,
        "description": "PyTorch — deep learning, commonly used in NLP/CV applications",
    },
    "pytorch": {
        "category": "ml_deep_learning",
        "hr_relevance": 0.5,
        "description": "PyTorch alias in some package managers",
    },
    "keras": {
        "category": "ml_deep_learning",
        "hr_relevance": 0.5,
        "description": "High-level deep learning API",
    },
    "xgboost": {
        "category": "ml_classical",
        "hr_relevance": 0.7,
        "description": "Gradient boosting — very common in tabular data scoring (candidate ranking)",
    },
    "lightgbm": {
        "category": "ml_classical",
        "hr_relevance": 0.7,
        "description": "Gradient boosting — fast training, common in scoring pipelines",
    },
    "catboost": {
        "category": "ml_classical",
        "hr_relevance": 0.6,
        "description": "Gradient boosting with categorical feature support",
    },

    # --- NLP (High HR Relevance — resume parsing, sentiment analysis) ---
    "spacy": {
        "category": "nlp",
        "hr_relevance": 0.8,
        "description": "NLP library — resume parsing, entity extraction from applications",
    },
    "nltk": {
        "category": "nlp",
        "hr_relevance": 0.6,
        "description": "Natural language toolkit — text processing",
    },
    "transformers": {
        "category": "nlp",
        "hr_relevance": 0.7,
        "description": "HuggingFace Transformers — pretrained models for NLP tasks",
    },
    "sentence-transformers": {
        "category": "nlp",
        "hr_relevance": 0.8,
        "description": "Sentence embeddings — semantic similarity for candidate matching",
    },
    "gensim": {
        "category": "nlp",
        "hr_relevance": 0.6,
        "description": "Topic modeling and document similarity",
    },
    "flair": {
        "category": "nlp",
        "hr_relevance": 0.6,
        "description": "NLP framework for sequence labeling and text classification",
    },

    # --- LLM / GenAI Frameworks ---
    "openai": {
        "category": "llm",
        "hr_relevance": 0.6,
        "description": "OpenAI API client — GPT models for text generation/analysis",
    },
    "anthropic": {
        "category": "llm",
        "hr_relevance": 0.6,
        "description": "Anthropic API client — Claude models",
    },
    "langchain": {
        "category": "llm_orchestration",
        "hr_relevance": 0.6,
        "description": "LLM orchestration framework — chains, agents, RAG",
    },
    "langchain-core": {
        "category": "llm_orchestration",
        "hr_relevance": 0.6,
        "description": "LangChain core abstractions",
    },
    "llama-index": {
        "category": "llm_orchestration",
        "hr_relevance": 0.5,
        "description": "Data framework for LLM applications, RAG pipelines",
    },
    "llamaindex": {
        "category": "llm_orchestration",
        "hr_relevance": 0.5,
        "description": "LlamaIndex alias",
    },
    "crewai": {
        "category": "llm_agents",
        "hr_relevance": 0.5,
        "description": "Multi-agent AI framework",
    },
    "autogen": {
        "category": "llm_agents",
        "hr_relevance": 0.5,
        "description": "Microsoft AutoGen — multi-agent conversations",
    },

    # --- Computer Vision ---
    "opencv-python": {
        "category": "cv",
        "hr_relevance": 0.3,
        "description": "Computer vision — less common in HR, used in ID verification",
    },
    "pillow": {
        "category": "cv",
        "hr_relevance": 0.1,
        "description": "Image processing — unlikely HR use",
    },
    "torchvision": {
        "category": "cv",
        "hr_relevance": 0.3,
        "description": "PyTorch vision models",
    },
    "ultralytics": {
        "category": "cv",
        "hr_relevance": 0.2,
        "description": "YOLO object detection",
    },

    # --- Data Processing (Supporting signals) ---
    "pandas": {
        "category": "data_processing",
        "hr_relevance": 0.3,
        "description": "Data manipulation — ubiquitous, weak signal alone",
        "is_ai_framework": False,
    },
    "numpy": {
        "category": "data_processing",
        "hr_relevance": 0.2,
        "description": "Numerical computing — very weak signal alone",
        "is_ai_framework": False,
    },
    "polars": {
        "category": "data_processing",
        "hr_relevance": 0.2,
        "description": "Fast dataframe library",
        "is_ai_framework": False,
    },

    # --- MLOps / Model Serving ---
    "mlflow": {
        "category": "mlops",
        "hr_relevance": 0.5,
        "description": "ML experiment tracking and model registry",
    },
    "wandb": {
        "category": "mlops",
        "hr_relevance": 0.5,
        "description": "Weights & Biases — experiment tracking",
    },
    "bentoml": {
        "category": "mlops",
        "hr_relevance": 0.4,
        "description": "Model serving framework",
    },

    # --- Fairness / Bias (Strong HR signal) ---
    "fairlearn": {
        "category": "fairness",
        "hr_relevance": 0.95,
        "description": "Fairness assessment and bias mitigation — very strong HR/hiring signal",
    },
    "aif360": {
        "category": "fairness",
        "hr_relevance": 0.95,
        "description": "IBM AI Fairness 360 — bias detection toolkit",
    },
    "themis-ml": {
        "category": "fairness",
        "hr_relevance": 0.9,
        "description": "Fairness-aware ML library",
    },
}


JS_FRAMEWORK_SIGNATURES: dict[str, dict] = {
    "tensorflow": {
        "category": "ml_deep_learning",
        "hr_relevance": 0.4,
        "description": "TensorFlow.js",
    },
    "@tensorflow/tfjs": {
        "category": "ml_deep_learning",
        "hr_relevance": 0.4,
        "description": "TensorFlow.js",
    },
    "openai": {
        "category": "llm",
        "hr_relevance": 0.6,
        "description": "OpenAI Node.js client",
    },
    "@anthropic-ai/sdk": {
        "category": "llm",
        "hr_relevance": 0.6,
        "description": "Anthropic Claude SDK",
    },
    "langchain": {
        "category": "llm_orchestration",
        "hr_relevance": 0.6,
        "description": "LangChain JS/TS",
    },
    "@langchain/core": {
        "category": "llm_orchestration",
        "hr_relevance": 0.6,
        "description": "LangChain core JS",
    },
    "llamaindex": {
        "category": "llm_orchestration",
        "hr_relevance": 0.5,
        "description": "LlamaIndex JS/TS",
    },
    "brain.js": {
        "category": "ml_deep_learning",
        "hr_relevance": 0.3,
        "description": "Neural network library for JS",
    },
    "ml5": {
        "category": "ml_general",
        "hr_relevance": 0.2,
        "description": "Friendly ML library for the web",
    },
}


class RequirementsParser:
    """Parses dependency manifests to detect ML/AI frameworks.

    Supports:
    - requirements.txt (Python)
    - pyproject.toml (Python)
    - package.json (JavaScript/TypeScript)
    - Pipfile (Python) — TODO
    - setup.py (Python) — TODO
    """

    def parse_requirements_txt(self, content: str) -> list[DetectedFramework]:
        """Parse a requirements.txt file and detect ML/AI frameworks."""
        detected: list[DetectedFramework] = []

        for line in content.strip().splitlines():
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Parse package name and optional version
            match = re.match(r"^([a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9_,-]+\])?)\s*([<>=!~].*)?$", line)
            if not match:
                continue

            pkg_name = match.group(1).split("[")[0].lower()  # Strip extras
            version = match.group(2)

            sig = PYTHON_FRAMEWORK_SIGNATURES.get(pkg_name)
            if sig:
                detected.append(DetectedFramework(
                    name=pkg_name,
                    version=version.strip() if version else None,
                    ecosystem=Ecosystem.PYTHON,
                    category=sig["category"],
                    hr_relevance_score=sig["hr_relevance"],
                    description=sig["description"],
                    is_ai_framework=sig.get("is_ai_framework", True),
                ))

        return detected

    def parse_package_json(self, content: str) -> list[DetectedFramework]:
        """Parse a package.json file and detect ML/AI frameworks."""
        detected: list[DetectedFramework] = []

        try:
            pkg = json.loads(content)
        except json.JSONDecodeError:
            return detected

        all_deps: dict[str, str] = {}
        all_deps.update(pkg.get("dependencies", {}))
        all_deps.update(pkg.get("devDependencies", {}))

        for dep_name, dep_version in all_deps.items():
            sig = JS_FRAMEWORK_SIGNATURES.get(dep_name)
            if sig:
                detected.append(DetectedFramework(
                    name=dep_name,
                    version=dep_version,
                    ecosystem=Ecosystem.JAVASCRIPT,
                    category=sig["category"],
                    hr_relevance_score=sig["hr_relevance"],
                    description=sig["description"],
                    is_ai_framework=sig.get("is_ai_framework", True),
                ))

        return detected

    def parse_pyproject_toml(self, content: str) -> list[DetectedFramework]:
        """Parse a pyproject.toml file and detect ML/AI frameworks."""
        import toml

        detected: list[DetectedFramework] = []

        try:
            data = toml.loads(content)
        except Exception:
            return detected

        # Check [project.dependencies]
        deps = data.get("project", {}).get("dependencies", [])

        # Check [tool.poetry.dependencies] (Poetry format)
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        if isinstance(poetry_deps, dict):
            deps.extend(poetry_deps.keys())

        for dep in deps:
            # Extract package name from PEP 508 string
            match = re.match(r"^([a-zA-Z0-9_-]+)", str(dep))
            if not match:
                continue

            pkg_name = match.group(1).lower()
            sig = PYTHON_FRAMEWORK_SIGNATURES.get(pkg_name)
            if sig:
                detected.append(DetectedFramework(
                    name=pkg_name,
                    version=None,
                    ecosystem=Ecosystem.PYTHON,
                    category=sig["category"],
                    hr_relevance_score=sig["hr_relevance"],
                    description=sig["description"],
                    is_ai_framework=sig.get("is_ai_framework", True),
                ))

        return detected

    def parse_all(
        self,
        files: dict[str, str],
    ) -> list[DetectedFramework]:
        """Parse multiple manifest files and return deduplicated results.

        Args:
            files: Dict mapping filename to file content.
                   e.g. {"requirements.txt": "scikit-learn==1.3.0\npandas\n"}
        """
        all_detected: list[DetectedFramework] = []
        seen: set[str] = set()

        parsers = {
            "requirements.txt": self.parse_requirements_txt,
            "package.json": self.parse_package_json,
            "pyproject.toml": self.parse_pyproject_toml,
        }

        for filename, content in files.items():
            for pattern, parser_fn in parsers.items():
                if filename.endswith(pattern):
                    for fw in parser_fn(content):
                        key = f"{fw.ecosystem}:{fw.name}"
                        if key not in seen:
                            seen.add(key)
                            all_detected.append(fw)

        return all_detected
