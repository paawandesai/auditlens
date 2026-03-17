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
