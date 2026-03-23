"""AST-based call-chain analysis for Python files.

Detects four regulated decision patterns where AI output flows into:
1. Conditional branching (if/switch on AI result)
2. Database persistence (AI output written to DB)
3. UI rendering (AI output displayed to users)
4. Downstream API calls (AI output sent to external services)

Uses Python's built-in ast module — zero new dependencies.
Pure function: receives pre-fetched content, returns findings.
"""

from __future__ import annotations

import ast
from typing import Literal

from app.schemas.scanner import CallChainFinding

# Database write patterns: {module_or_method: description}
_DB_WRITE_METHODS: set[str] = {
    # SQLAlchemy
    "add", "execute", "commit", "merge", "bulk_save_objects",
    # Django ORM
    "save", "create", "update", "bulk_create", "bulk_update",
    # Raw SQL
    "executemany",
    # MongoDB
    "insert_one", "insert_many", "update_one", "update_many",
    "replace_one",
}

# HTTP client methods that indicate downstream API calls
_HTTP_METHODS: set[str] = {
    "post", "put", "patch",
}

# UI rendering methods
_UI_RENDER_METHODS: set[str] = {
    # Flask
    "render_template", "render_template_string",
    # FastAPI / Starlette
    "JSONResponse", "HTMLResponse", "PlainTextResponse",
    # Django
    "render",
    # Generic
    "json", "send_json", "jsonify",
}


class _AICallChainVisitor(ast.NodeVisitor):
    """Walk AST to find AI calls and trace their outputs to decision points."""

    def __init__(self, ai_modules: set[str], filename: str) -> None:
        self.ai_modules = ai_modules
        self.filename = filename
        # Variables that hold AI output: var_name → (framework, line)
        self.ai_variables: dict[str, tuple[str, int]] = {}
        self.findings: list[CallChainFinding] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check if RHS is an AI API call and track the assigned variable."""
        framework = self._extract_ai_call_framework(node.value)
        if framework:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.ai_variables[target.id] = (framework, node.lineno)
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            self.ai_variables[elt.id] = (framework, node.lineno)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Check if test references an AI variable (conditional branching)."""
        refs = self._extract_names(node.test)
        for ref in refs:
            if ref in self.ai_variables:
                framework, ai_line = self.ai_variables[ref]
                self.findings.append(CallChainFinding(
                    pattern="conditional_branching",
                    ai_call_file=self.filename,
                    ai_call_line=ai_line,
                    ai_framework=framework,
                    decision_file=self.filename,
                    decision_line=node.lineno,
                    decision_context=f"if {ref} ... (line {node.lineno})",
                    severity="critical",
                ))
                break
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Check standalone expression calls for DB writes and API calls."""
        if isinstance(node.value, ast.Call):
            self._check_call_for_patterns(node.value, node.lineno)
        elif isinstance(node.value, ast.Await) and isinstance(node.value.value, ast.Call):
            self._check_call_for_patterns(node.value.value, node.lineno)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Check if AI variable is returned (potential UI rendering)."""
        if node.value:
            refs = self._extract_names(node.value)
            for ref in refs:
                if ref in self.ai_variables:
                    framework, ai_line = self.ai_variables[ref]
                    self.findings.append(CallChainFinding(
                        pattern="ui_rendering",
                        ai_call_file=self.filename,
                        ai_call_line=ai_line,
                        ai_framework=framework,
                        decision_file=self.filename,
                        decision_line=node.lineno,
                        decision_context=f"return {ref} (line {node.lineno})",
                        severity="warning",
                    ))
                    break
        self.generic_visit(node)

    def _check_call_for_patterns(self, call: ast.Call, lineno: int) -> None:
        """Check if a function call uses AI variables in DB/API/UI patterns."""
        method_name = self._get_method_name(call)
        if not method_name:
            return

        # Check if any argument references an AI variable
        ai_ref = self._find_ai_arg(call)
        if not ai_ref:
            return

        framework, ai_line = self.ai_variables[ai_ref]

        if method_name in _DB_WRITE_METHODS:
            self.findings.append(CallChainFinding(
                pattern="database_persistence",
                ai_call_file=self.filename,
                ai_call_line=ai_line,
                ai_framework=framework,
                decision_file=self.filename,
                decision_line=lineno,
                decision_context=f"{method_name}({ai_ref}) (line {lineno})",
                severity="critical",
            ))
        elif method_name in _HTTP_METHODS:
            self.findings.append(CallChainFinding(
                pattern="downstream_api_call",
                ai_call_file=self.filename,
                ai_call_line=ai_line,
                ai_framework=framework,
                decision_file=self.filename,
                decision_line=lineno,
                decision_context=f"{method_name}(..., {ai_ref}) (line {lineno})",
                severity="warning",
            ))
        elif method_name in _UI_RENDER_METHODS:
            self.findings.append(CallChainFinding(
                pattern="ui_rendering",
                ai_call_file=self.filename,
                ai_call_line=ai_line,
                ai_framework=framework,
                decision_file=self.filename,
                decision_line=lineno,
                decision_context=f"{method_name}({ai_ref}) (line {lineno})",
                severity="warning",
            ))

    def _extract_ai_call_framework(self, node: ast.expr) -> str | None:
        """Check if a node is a call to an AI module. Returns framework name or None."""
        call = node
        if isinstance(node, ast.Await):
            call = node.value
        if not isinstance(call, ast.Call):
            return None

        # Get the full dotted name of the function being called
        parts = self._get_dotted_name(call.func)
        if not parts:
            return None

        top_module = parts[0]
        if top_module in self.ai_modules:
            return top_module
        return None

    def _get_dotted_name(self, node: ast.expr) -> list[str]:
        """Extract dotted name parts from an attribute chain."""
        if isinstance(node, ast.Name):
            return [node.id]
        if isinstance(node, ast.Attribute):
            parent = self._get_dotted_name(node.value)
            if parent:
                return parent + [node.attr]
        return []

    def _get_method_name(self, call: ast.Call) -> str | None:
        """Extract the method name from a call node."""
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        if isinstance(call.func, ast.Name):
            return call.func.id
        return None

    def _find_ai_arg(self, call: ast.Call) -> str | None:
        """Find the first argument that references an AI variable."""
        for arg in call.args:
            refs = self._extract_names(arg)
            for ref in refs:
                if ref in self.ai_variables:
                    return ref
        for kw in call.keywords:
            if kw.value:
                refs = self._extract_names(kw.value)
                for ref in refs:
                    if ref in self.ai_variables:
                        return ref
        return None

    def _extract_names(self, node: ast.expr) -> list[str]:
        """Extract all Name references from an expression."""
        names: list[str] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.append(child.id)
        return names


def analyze_call_chains(
    content: str,
    filename: str,
    ai_modules: set[str],
) -> list[CallChainFinding]:
    """Analyze a Python file for call-chain patterns.

    Args:
        content: Python source code.
        filename: File path for reporting.
        ai_modules: Set of top-level AI module names to track.

    Returns:
        List of CallChainFinding describing detected patterns.
    """
    if not ai_modules:
        return []

    try:
        tree = ast.parse(content, filename=filename or "<string>")
    except SyntaxError:
        return []

    visitor = _AICallChainVisitor(ai_modules, filename)
    visitor.visit(tree)
    return visitor.findings
