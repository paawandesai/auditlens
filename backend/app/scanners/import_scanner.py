# Scanning patterns adapted from Systima Comply (Apache 2.0)
# https://github.com/systima-ai/comply
"""Python import scanning via AST with regex fallback.

AST-based scanning provides file + line number precision for detected
frameworks. Falls back to regex for files with syntax errors.

Pure function — receives pre-fetched file content.
"""

from __future__ import annotations

import ast
import re

from app.scanners.requirements_parser import PYTHON_FRAMEWORK_SIGNATURES
from app.schemas.scanner import DetectedFramework, DetectedImport

# Regex fallback for files with syntax errors
_IMPORT_RE = re.compile(
    r"^(?:import\s+([\w.]+)|from\s+([\w.]+)\s+import)",
    re.MULTILINE,
)

# Confidence penalty for import-based detection vs manifest-based
_IMPORT_CONFIDENCE_PENALTY = 0.15

# Map top-level module names to their pip package names
_MODULE_TO_PACKAGE: dict[str, str] = {
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "tf": "tensorflow",
    "np": "numpy",
    "pd": "pandas",
    "hf_hub": "huggingface-hub",
}

# File path patterns to target for import scanning
IMPORT_SCAN_PATTERNS: list[str] = [
    "main.py", "app.py", "run.py", "server.py", "api.py",
]

# Glob-style patterns for deeper matches (matched case-insensitively)
IMPORT_SCAN_GLOBS: list[str] = [
    "model", "predict", "train", "pipeline", "inference",
    "agent", "llm", "chat",
    "routes/", "routers/", "views/", "endpoints/",
]

# Expanded limit for AST scanning (was 5 for regex)
MAX_IMPORT_FILES = 30


def scan_python_imports_ast(
    content: str,
    filename: str = "",
    framework_sigs: dict[str, dict] | None = None,
) -> tuple[list[DetectedFramework], list[DetectedImport]]:
    """AST-based import detection with file + line number precision.

    Falls back to regex for files with syntax errors.

    Args:
        content: Raw Python source code content.
        filename: The file path (for error reporting and DetectedImport).
        framework_sigs: Framework signature dict (defaults to PYTHON_FRAMEWORK_SIGNATURES).

    Returns:
        Tuple of (DetectedFramework list for backward compat, DetectedImport list with locations).
    """
    if framework_sigs is None:
        framework_sigs = PYTHON_FRAMEWORK_SIGNATURES

    try:
        tree = ast.parse(content, filename=filename or "<string>")
    except SyntaxError:
        # Fallback to regex for malformed files
        frameworks = scan_python_imports_regex(content, framework_sigs)
        return frameworks, []

    raw_imports: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                raw_imports.append((alias.name, node.lineno, node.col_offset))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                raw_imports.append((node.module, node.lineno, node.col_offset))

    seen: set[str] = set()
    frameworks: list[DetectedFramework] = []
    imports: list[DetectedImport] = []

    for module_path, line, col in raw_imports:
        top_module = module_path.split(".")[0]
        pkg_name = _MODULE_TO_PACKAGE.get(top_module, top_module).lower()

        sig = framework_sigs.get(pkg_name)
        if sig and pkg_name not in seen:
            seen.add(pkg_name)
            confidence = max(sig["confidence"] - _IMPORT_CONFIDENCE_PENALTY, 0.1)
            frameworks.append(DetectedFramework(
                name=pkg_name,
                version=None,
                confidence=confidence,
                hr_relevance_score=sig["hr_relevance"],
            ))
            imports.append(DetectedImport(
                module=module_path,
                package=pkg_name,
                framework=pkg_name,
                file=filename,
                line=line,
                col=col,
                confidence=confidence,
                hr_relevance_score=sig["hr_relevance"],
            ))

    return frameworks, imports


def scan_python_imports_regex(
    content: str,
    framework_sigs: dict[str, dict] | None = None,
) -> list[DetectedFramework]:
    """Regex fallback for files with syntax errors."""
    if framework_sigs is None:
        framework_sigs = PYTHON_FRAMEWORK_SIGNATURES

    seen: set[str] = set()
    results: list[DetectedFramework] = []

    for match in _IMPORT_RE.finditer(content):
        module_path = match.group(1) or match.group(2)
        if not module_path:
            continue

        top_module = module_path.split(".")[0]
        pkg_name = _MODULE_TO_PACKAGE.get(top_module, top_module).lower()

        if pkg_name in seen:
            continue

        sig = framework_sigs.get(pkg_name)
        if sig:
            seen.add(pkg_name)
            confidence = max(sig["confidence"] - _IMPORT_CONFIDENCE_PENALTY, 0.1)
            results.append(DetectedFramework(
                name=pkg_name,
                version=None,
                confidence=confidence,
                hr_relevance_score=sig["hr_relevance"],
            ))

    return results


# Backward-compatible wrapper
def scan_python_imports(
    content: str,
    framework_sigs: dict[str, dict] | None = None,
) -> list[DetectedFramework]:
    """Scan Python source for AI/ML framework imports (backward-compatible).

    Delegates to AST scanner, returns only DetectedFramework list.
    """
    frameworks, _ = scan_python_imports_ast(content, framework_sigs=framework_sigs)
    return frameworks


def select_python_files(file_paths: list[str]) -> list[str]:
    """Select Python files worth scanning for imports.

    Picks files matching known AI/ML entry-point patterns, capped at MAX_IMPORT_FILES.
    """
    candidates: list[str] = []

    for path in file_paths:
        if not path.endswith(".py"):
            continue

        filename = path.rsplit("/", 1)[-1].lower()
        path_lower = path.lower()

        # Direct name matches
        if filename in IMPORT_SCAN_PATTERNS:
            candidates.append(path)
            continue

        # Glob-style pattern matches
        if any(pat in path_lower for pat in IMPORT_SCAN_GLOBS):
            candidates.append(path)

    # Deduplicate preserving order, cap at limit
    seen: set[str] = set()
    unique: list[str] = []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return unique[:MAX_IMPORT_FILES]


def merge_frameworks(
    manifest_frameworks: list[DetectedFramework],
    import_frameworks: list[DetectedFramework],
) -> list[DetectedFramework]:
    """Merge manifest-detected and import-detected frameworks, deduping by name.

    When the same framework is detected by both methods, keeps the one with
    higher confidence (typically the manifest detection).
    """
    by_name: dict[str, DetectedFramework] = {}

    for fw in manifest_frameworks:
        by_name[fw.name] = fw

    for fw in import_frameworks:
        existing = by_name.get(fw.name)
        if existing is None or fw.confidence > existing.confidence:
            by_name[fw.name] = fw

    return list(by_name.values())
