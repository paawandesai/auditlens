"""JS/TS import scanning via tree-sitter for AI/ML framework detection.

Provides file + line number precision for JavaScript and TypeScript imports.
Falls back to regex when tree-sitter is not available.

Pure function — receives pre-fetched file content.
"""

from __future__ import annotations

import re

from app.scanners.requirements_parser import JS_FRAMEWORK_SIGNATURES
from app.schemas.scanner import DetectedFramework, DetectedImport

# Confidence penalty for import-based detection vs manifest (package.json)
_IMPORT_CONFIDENCE_PENALTY = 0.15

# Regex fallback for JS/TS imports
_JS_IMPORT_RE = re.compile(
    r"""(?:
        import\s+.*?\s+from\s+['"]([^'"]+)['"]  |  # import X from 'pkg'
        require\s*\(\s*['"]([^'"]+)['"]\s*\)       # require('pkg')
    )""",
    re.MULTILINE | re.VERBOSE,
)

# File patterns to target for JS/TS import scanning
JS_IMPORT_SCAN_PATTERNS: list[str] = [
    "index.js", "index.ts", "index.tsx",
    "app.js", "app.ts", "app.tsx",
    "server.js", "server.ts",
    "main.js", "main.ts",
]

JS_IMPORT_SCAN_GLOBS: list[str] = [
    "api", "route", "handler", "middleware",
    "model", "agent", "llm", "chat",
]

MAX_JS_IMPORT_FILES = 25


def _try_tree_sitter() -> bool:
    """Check if tree-sitter and language bindings are available."""
    try:
        import tree_sitter  # noqa: F401
        import tree_sitter_javascript  # noqa: F401
        return True
    except ImportError:
        return False


def scan_js_imports_tree_sitter(
    content: str,
    filename: str,
    framework_sigs: dict[str, dict] | None = None,
) -> tuple[list[DetectedFramework], list[DetectedImport]]:
    """Tree-sitter-based JS/TS import detection with line numbers."""
    if framework_sigs is None:
        framework_sigs = JS_FRAMEWORK_SIGNATURES

    import tree_sitter_javascript as tsjs
    from tree_sitter import Language, Parser

    is_ts = filename.endswith((".ts", ".tsx"))

    if is_ts:
        try:
            import tree_sitter_typescript as tsts
            lang = Language(tsts.language_typescript())
        except ImportError:
            lang = Language(tsjs.language())
    else:
        lang = Language(tsjs.language())

    parser = Parser(lang)
    tree = parser.parse(content.encode())

    seen: set[str] = set()
    frameworks: list[DetectedFramework] = []
    imports: list[DetectedImport] = []

    def _walk(node):  # noqa: ANN001
        # import_statement: import X from 'pkg'
        if node.type in ("import_statement", "import_declaration"):
            source_node = node.child_by_field_name("source")
            if source_node:
                pkg = source_node.text.decode().strip("'\"")
                _process_package(pkg, node.start_point[0] + 1, node.start_point[1])

        # call_expression: require('pkg')
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func and func.text == b"require":
                args = node.child_by_field_name("arguments")
                if args and args.child_count > 1:
                    string_node = args.children[1]
                    if string_node.type == "string":
                        pkg = string_node.text.decode().strip("'\"")
                        _process_package(
                            pkg, node.start_point[0] + 1, node.start_point[1],
                        )

        for child in node.children:
            _walk(child)

    def _process_package(pkg: str, line: int, col: int) -> None:
        # Normalize scoped packages: @scope/name → @scope/name
        pkg_key = pkg.lower()
        if pkg_key in seen:
            return

        sig = framework_sigs.get(pkg_key)
        if not sig:
            # Try without scope for partial matches
            base = pkg_key.split("/")[-1] if "/" in pkg_key else pkg_key
            sig = framework_sigs.get(base)

        if sig:
            seen.add(pkg_key)
            confidence = max(sig["confidence"] - _IMPORT_CONFIDENCE_PENALTY, 0.1)
            frameworks.append(DetectedFramework(
                name=pkg_key,
                version=None,
                confidence=confidence,
                hr_relevance_score=sig["hr_relevance"],
            ))
            imports.append(DetectedImport(
                module=pkg,
                package=pkg_key,
                framework=pkg_key,
                file=filename,
                line=line,
                col=col,
                confidence=confidence,
                hr_relevance_score=sig["hr_relevance"],
            ))

    _walk(tree.root_node)
    return frameworks, imports


def scan_js_imports_regex(
    content: str,
    filename: str = "",
    framework_sigs: dict[str, dict] | None = None,
) -> tuple[list[DetectedFramework], list[DetectedImport]]:
    """Regex fallback for JS/TS import detection."""
    if framework_sigs is None:
        framework_sigs = JS_FRAMEWORK_SIGNATURES

    seen: set[str] = set()
    frameworks: list[DetectedFramework] = []
    imports: list[DetectedImport] = []

    for match in _JS_IMPORT_RE.finditer(content):
        pkg = match.group(1) or match.group(2)
        if not pkg:
            continue

        pkg_key = pkg.lower()
        if pkg_key in seen:
            continue

        sig = framework_sigs.get(pkg_key)
        if not sig:
            base = pkg_key.split("/")[-1] if "/" in pkg_key else pkg_key
            sig = framework_sigs.get(base)

        if sig:
            seen.add(pkg_key)
            line = content[:match.start()].count("\n") + 1
            confidence = max(sig["confidence"] - _IMPORT_CONFIDENCE_PENALTY, 0.1)
            frameworks.append(DetectedFramework(
                name=pkg_key,
                version=None,
                confidence=confidence,
                hr_relevance_score=sig["hr_relevance"],
            ))
            imports.append(DetectedImport(
                module=pkg,
                package=pkg_key,
                framework=pkg_key,
                file=filename,
                line=line,
                col=0,
                confidence=confidence,
                hr_relevance_score=sig["hr_relevance"],
            ))

    return frameworks, imports


def scan_js_imports(
    content: str,
    filename: str = "",
    framework_sigs: dict[str, dict] | None = None,
) -> tuple[list[DetectedFramework], list[DetectedImport]]:
    """Scan JS/TS source for AI/ML framework imports.

    Uses tree-sitter when available, falls back to regex.
    """
    if _try_tree_sitter():
        return scan_js_imports_tree_sitter(content, filename, framework_sigs)
    return scan_js_imports_regex(content, filename, framework_sigs)


def select_js_files(file_paths: list[str]) -> list[str]:
    """Select JS/TS files worth scanning for imports."""
    js_extensions = (".js", ".ts", ".tsx", ".jsx", ".mjs")
    candidates: list[str] = []

    for path in file_paths:
        if not any(path.endswith(ext) for ext in js_extensions):
            continue

        filename = path.rsplit("/", 1)[-1].lower()
        path_lower = path.lower()

        if filename in JS_IMPORT_SCAN_PATTERNS:
            candidates.append(path)
            continue

        if any(pat in path_lower for pat in JS_IMPORT_SCAN_GLOBS):
            candidates.append(path)

    seen: set[str] = set()
    unique: list[str] = []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return unique[:MAX_JS_IMPORT_FILES]
