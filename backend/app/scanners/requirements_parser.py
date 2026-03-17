"""Dependency manifest parser — detects ML/AI frameworks.

Parses requirements.txt, pyproject.toml, package.json, Pipfile, and setup.cfg
to detect known ML/AI frameworks. Returns Pydantic DetectedFramework models
compatible with the ScannerOutput schema.

Ported from tmp/requirements_parser.py with Pydantic output models.
"""

from __future__ import annotations

import json
import re

from app.schemas.scanner import DetectedFramework

# ---------------------------------------------------------------------------
# Framework Signature Database
# ---------------------------------------------------------------------------

PYTHON_FRAMEWORK_SIGNATURES: dict[str, dict] = {
    # Core ML
    "scikit-learn": {"hr_relevance": 0.7, "confidence": 0.95},
    "sklearn": {"hr_relevance": 0.7, "confidence": 0.95},
    "tensorflow": {"hr_relevance": 0.5, "confidence": 0.95},
    "torch": {"hr_relevance": 0.5, "confidence": 0.95},
    "pytorch": {"hr_relevance": 0.5, "confidence": 0.95},
    "keras": {"hr_relevance": 0.5, "confidence": 0.90},
    "xgboost": {"hr_relevance": 0.7, "confidence": 0.95},
    "lightgbm": {"hr_relevance": 0.7, "confidence": 0.95},
    "catboost": {"hr_relevance": 0.6, "confidence": 0.95},
    # NLP
    "spacy": {"hr_relevance": 0.8, "confidence": 0.90},
    "nltk": {"hr_relevance": 0.6, "confidence": 0.85},
    "transformers": {"hr_relevance": 0.7, "confidence": 0.90},
    "sentence-transformers": {"hr_relevance": 0.8, "confidence": 0.90},
    "gensim": {"hr_relevance": 0.6, "confidence": 0.85},
    "flair": {"hr_relevance": 0.6, "confidence": 0.85},
    # LLM
    "openai": {"hr_relevance": 0.6, "confidence": 0.90},
    "anthropic": {"hr_relevance": 0.6, "confidence": 0.90},
    "langchain": {"hr_relevance": 0.6, "confidence": 0.85},
    "langchain-core": {"hr_relevance": 0.6, "confidence": 0.85},
    "llama-index": {"hr_relevance": 0.5, "confidence": 0.85},
    "llamaindex": {"hr_relevance": 0.5, "confidence": 0.85},
    "crewai": {"hr_relevance": 0.5, "confidence": 0.80},
    "autogen": {"hr_relevance": 0.5, "confidence": 0.80},
    # CV
    "opencv-python": {"hr_relevance": 0.3, "confidence": 0.90},
    "torchvision": {"hr_relevance": 0.3, "confidence": 0.90},
    "ultralytics": {"hr_relevance": 0.2, "confidence": 0.90},
    # Data processing (weaker signals)
    "pandas": {"hr_relevance": 0.3, "confidence": 0.60},
    "numpy": {"hr_relevance": 0.2, "confidence": 0.50},
    "polars": {"hr_relevance": 0.2, "confidence": 0.55},
    # MLOps
    "mlflow": {"hr_relevance": 0.5, "confidence": 0.90},
    "wandb": {"hr_relevance": 0.5, "confidence": 0.90},
    "bentoml": {"hr_relevance": 0.4, "confidence": 0.85},
    # Fairness (very strong HR signal)
    "fairlearn": {"hr_relevance": 0.95, "confidence": 0.98},
    "aif360": {"hr_relevance": 0.95, "confidence": 0.98},
    "themis-ml": {"hr_relevance": 0.9, "confidence": 0.95},
    # LLM Providers (ported from Comply)
    "cohere": {"hr_relevance": 0.6, "confidence": 0.90},
    "mistralai": {"hr_relevance": 0.6, "confidence": 0.90},
    "google-generativeai": {"hr_relevance": 0.6, "confidence": 0.90},
    "together": {"hr_relevance": 0.5, "confidence": 0.85},
    "groq": {"hr_relevance": 0.5, "confidence": 0.85},
    "replicate": {"hr_relevance": 0.5, "confidence": 0.85},
    "boto3": {"hr_relevance": 0.3, "confidence": 0.50},
    # Agent frameworks
    "semantic-kernel": {"hr_relevance": 0.5, "confidence": 0.85},
    "haystack-ai": {"hr_relevance": 0.5, "confidence": 0.85},
    "dspy-ai": {"hr_relevance": 0.5, "confidence": 0.80},
    # Computer Vision (high HR relevance — face recognition = biometrics)
    "face-recognition": {"hr_relevance": 0.95, "confidence": 0.98},
    "deepface": {"hr_relevance": 0.95, "confidence": 0.98},
    "insightface": {"hr_relevance": 0.95, "confidence": 0.98},
    "mediapipe": {"hr_relevance": 0.7, "confidence": 0.90},
}

JS_FRAMEWORK_SIGNATURES: dict[str, dict] = {
    "tensorflow": {"hr_relevance": 0.4, "confidence": 0.90},
    "@tensorflow/tfjs": {"hr_relevance": 0.4, "confidence": 0.90},
    "openai": {"hr_relevance": 0.6, "confidence": 0.90},
    "@anthropic-ai/sdk": {"hr_relevance": 0.6, "confidence": 0.90},
    "langchain": {"hr_relevance": 0.6, "confidence": 0.85},
    "@langchain/core": {"hr_relevance": 0.6, "confidence": 0.85},
    "llamaindex": {"hr_relevance": 0.5, "confidence": 0.85},
    "brain.js": {"hr_relevance": 0.3, "confidence": 0.80},
    "ml5": {"hr_relevance": 0.2, "confidence": 0.75},
    # Ported from Comply
    "@google/generative-ai": {"hr_relevance": 0.6, "confidence": 0.90},
    "cohere-ai": {"hr_relevance": 0.6, "confidence": 0.90},
    "@vercel/ai": {"hr_relevance": 0.5, "confidence": 0.85},
    "ai": {"hr_relevance": 0.5, "confidence": 0.80},
    "mastra": {"hr_relevance": 0.5, "confidence": 0.80},
}


class RequirementsParser:
    """Parses dependency manifests to detect ML/AI frameworks.

    Returns Pydantic DetectedFramework models compatible with ScannerOutput.
    """

    def parse(self, files: dict[str, str]) -> list[DetectedFramework]:
        """Parse all manifest files, return deduplicated detected frameworks.

        Args:
            files: dict mapping filename → content
                   e.g. {"requirements.txt": "scikit-learn==1.4\\n..."}
        """
        all_detected: list[DetectedFramework] = []
        seen: set[str] = set()

        parsers: dict[str, callable] = {
            "requirements.txt": self._parse_requirements_txt,
            "package.json": self._parse_package_json,
            "pyproject.toml": self._parse_pyproject_toml,
            "Pipfile": self._parse_pipfile,
            "setup.cfg": self._parse_setup_cfg,
            "setup.py": self._parse_setup_py,
            "environment.yml": self._parse_environment_yml,
        }

        for filename, content in files.items():
            for pattern, parser_fn in parsers.items():
                if filename.endswith(pattern):
                    for fw in parser_fn(content):
                        if fw.name not in seen:
                            seen.add(fw.name)
                            all_detected.append(fw)

        return all_detected

    def _parse_requirements_txt(self, content: str) -> list[DetectedFramework]:
        detected: list[DetectedFramework] = []
        for line in content.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            match = re.match(
                r"^([a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9_,-]+\])?)\s*([<>=!~].*)?$", line
            )
            if not match:
                continue

            pkg_name = match.group(1).split("[")[0].lower()
            version = match.group(2)

            sig = PYTHON_FRAMEWORK_SIGNATURES.get(pkg_name)
            if sig:
                detected.append(DetectedFramework(
                    name=pkg_name,
                    version=version.strip() if version else None,
                    confidence=sig["confidence"],
                    hr_relevance_score=sig["hr_relevance"],
                ))
        return detected

    def _parse_package_json(self, content: str) -> list[DetectedFramework]:
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
                    version=dep_version if isinstance(dep_version, str) else None,
                    confidence=sig["confidence"],
                    hr_relevance_score=sig["hr_relevance"],
                ))
        return detected

    def _parse_pyproject_toml(self, content: str) -> list[DetectedFramework]:
        detected: list[DetectedFramework] = []
        deps: list[str] = []

        # Simple TOML parsing without external dependency
        # Extract [project.dependencies] array
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "[project]":
                continue
            if re.match(r"^\[", stripped) and "dependencies" not in stripped:
                in_deps = False
                continue
            if "dependencies" in stripped and "=" in stripped:
                in_deps = True
                # Handle inline array: dependencies = ["pkg1", "pkg2"]
                inline = re.findall(r'"([^"]+)"', stripped)
                deps.extend(inline)
                if "]" in stripped:
                    in_deps = False
                continue
            if in_deps:
                if "]" in stripped:
                    in_deps = False
                pkg_match = re.findall(r'"([^"]+)"', stripped)
                deps.extend(pkg_match)

        for dep in deps:
            pkg_match = re.match(r"^([a-zA-Z0-9_-]+)", dep)
            if not pkg_match:
                continue
            pkg_name = pkg_match.group(1).lower()
            sig = PYTHON_FRAMEWORK_SIGNATURES.get(pkg_name)
            if sig:
                detected.append(DetectedFramework(
                    name=pkg_name,
                    version=None,
                    confidence=sig["confidence"],
                    hr_relevance_score=sig["hr_relevance"],
                ))
        return detected

    def _parse_pipfile(self, content: str) -> list[DetectedFramework]:
        detected: list[DetectedFramework] = []
        in_packages = False

        for line in content.splitlines():
            stripped = line.strip()
            if stripped in ("[packages]", "[dev-packages]"):
                in_packages = True
                continue
            if stripped.startswith("["):
                in_packages = False
                continue
            if in_packages and "=" in stripped:
                pkg_name = stripped.split("=")[0].strip().strip('"').lower()
                sig = PYTHON_FRAMEWORK_SIGNATURES.get(pkg_name)
                if sig:
                    detected.append(DetectedFramework(
                        name=pkg_name,
                        version=None,
                        confidence=sig["confidence"],
                        hr_relevance_score=sig["hr_relevance"],
                    ))
        return detected

    def _parse_setup_cfg(self, content: str) -> list[DetectedFramework]:
        detected: list[DetectedFramework] = []
        in_install_requires = False

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("install_requires"):
                in_install_requires = True
                continue
            if in_install_requires:
                if stripped and not stripped.startswith("#"):
                    if not stripped.startswith(" ") and "=" in stripped:
                        break
                    pkg_match = re.match(r"^([a-zA-Z0-9_-]+)", stripped)
                    if pkg_match:
                        pkg_name = pkg_match.group(1).lower()
                        sig = PYTHON_FRAMEWORK_SIGNATURES.get(pkg_name)
                        if sig:
                            detected.append(DetectedFramework(
                                name=pkg_name,
                                version=None,
                                confidence=sig["confidence"],
                                hr_relevance_score=sig["hr_relevance"],
                            ))
        return detected

    def _parse_setup_py(self, content: str) -> list[DetectedFramework]:
        """Extract install_requires from setup.py using regex.

        Handles the common pattern: install_requires=["pkg1", "pkg2>=1.0"]
        Won't catch dynamic setup.py files that compute deps at runtime.
        """
        detected: list[DetectedFramework] = []

        # Match install_requires=[...] across multiple lines
        match = re.search(
            r"install_requires\s*=\s*\[([^\]]*)\]", content, re.DOTALL
        )
        if not match:
            return detected

        deps_block = match.group(1)
        dep_strings = re.findall(r"['\"]([^'\"]+)['\"]", deps_block)

        for dep in dep_strings:
            pkg_match = re.match(r"^([a-zA-Z0-9_-]+)", dep)
            if not pkg_match:
                continue
            pkg_name = pkg_match.group(1).lower()
            sig = PYTHON_FRAMEWORK_SIGNATURES.get(pkg_name)
            if sig:
                detected.append(DetectedFramework(
                    name=pkg_name,
                    version=None,
                    confidence=sig["confidence"],
                    hr_relevance_score=sig["hr_relevance"],
                ))
        return detected

    def _parse_environment_yml(self, content: str) -> list[DetectedFramework]:
        """Extract pip and conda dependencies from environment.yml.

        Parses both top-level conda deps and nested pip deps:
          dependencies:
            - numpy=1.21
            - pip:
              - scikit-learn>=1.0
        """
        detected: list[DetectedFramework] = []
        in_dependencies = False
        in_pip = False

        for line in content.splitlines():
            stripped = line.strip()

            if stripped.startswith("dependencies:"):
                in_dependencies = True
                continue

            if in_dependencies and stripped and not stripped.startswith("-") and ":" in stripped:
                # New top-level YAML key — exit dependencies block
                if not stripped.startswith("- pip"):
                    in_dependencies = False
                    in_pip = False
                    continue

            if not in_dependencies:
                continue

            if stripped == "- pip:":
                in_pip = True
                continue

            if stripped.startswith("- "):
                dep_str = stripped[2:].strip()
                # Extract package name (before version specifiers)
                pkg_match = re.match(r"^([a-zA-Z0-9_-]+)", dep_str)
                if not pkg_match:
                    continue
                pkg_name = pkg_match.group(1).lower()
                sig = PYTHON_FRAMEWORK_SIGNATURES.get(pkg_name)
                if sig:
                    detected.append(DetectedFramework(
                        name=pkg_name,
                        version=None,
                        confidence=sig["confidence"],
                        hr_relevance_score=sig["hr_relevance"],
                    ))

        return detected
