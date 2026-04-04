"""Tests for JS/TS import scanner (regex fallback path)."""

from __future__ import annotations

import pytest

from app.scanners.js_import_scanner import (
    scan_js_imports_regex,
    select_js_files,
)


class TestScanJsImportsRegex:
    """Test regex-based JS/TS import scanning."""

    def test_es6_import(self):
        code = "import { OpenAI } from 'openai';\n"
        frameworks, imports = scan_js_imports_regex(code, "app.js")
        assert len(frameworks) >= 1
        assert frameworks[0].name == "openai"
        assert len(imports) >= 1
        assert imports[0].line == 1
        assert imports[0].file == "app.js"

    def test_require_import(self):
        code = "const tf = require('tensorflow');\n"
        # tensorflow is not in JS sigs by default, use a known one
        code = "const openai = require('openai');\n"
        frameworks, imports = scan_js_imports_regex(code, "server.js")
        names = [f.name for f in frameworks]
        assert "openai" in names

    def test_no_ai_imports(self):
        code = "import React from 'react';\nimport express from 'express';\n"
        frameworks, imports = scan_js_imports_regex(code, "app.js")
        assert len(frameworks) == 0
        assert len(imports) == 0

    def test_empty_content(self):
        frameworks, imports = scan_js_imports_regex("", "empty.js")
        assert frameworks == []
        assert imports == []

    def test_deduplication(self):
        code = """\
import OpenAI from 'openai';
const client = require('openai');
"""
        frameworks, imports = scan_js_imports_regex(code, "app.js")
        names = [f.name for f in frameworks]
        assert names.count("openai") == 1

    def test_scoped_package(self):
        code = "import { Anthropic } from '@anthropic-ai/sdk';\n"
        frameworks, imports = scan_js_imports_regex(code, "app.ts")
        names = [f.name for f in frameworks]
        assert "@anthropic-ai/sdk" in names

    def test_confidence_penalty(self):
        code = "import OpenAI from 'openai';\n"
        frameworks, _ = scan_js_imports_regex(code, "app.js")
        assert len(frameworks) >= 1
        # Import detection applies 0.15 penalty
        assert frameworks[0].confidence < 1.0


class TestSelectJsFiles:
    """Test JS/TS file selection."""

    def test_selects_entry_points(self):
        paths = ["index.js", "index.ts", "app.tsx", "server.ts"]
        result = select_js_files(paths)
        assert "index.js" in result
        assert "index.ts" in result

    def test_selects_pattern_matches(self):
        paths = ["src/api/handler.ts", "routes/users.js", "middleware/auth.ts"]
        result = select_js_files(paths)
        assert len(result) >= 2

    def test_excludes_non_js(self):
        paths = ["model.py", "train.go", "handler.rs"]
        result = select_js_files(paths)
        assert result == []

    def test_cap_at_limit(self):
        paths = [f"routes/route{i}.ts" for i in range(20)]
        result = select_js_files(paths)
        assert len(result) <= 25

    def test_deduplication(self):
        paths = ["index.js", "index.js", "index.js"]
        result = select_js_files(paths)
        assert result == ["index.js"]
