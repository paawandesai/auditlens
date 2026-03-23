"""Tests for AST-based call-chain analysis."""

from __future__ import annotations

import pytest

from app.scanners.call_chain_analyzer import analyze_call_chains


class TestConditionalBranching:
    """Detect AI output used in conditional branching."""

    def test_simple_if(self):
        code = """\
import openai
result = openai.chat.completions.create(model="gpt-4", messages=[])
if result.choices[0].message.content:
    print("yes")
"""
        findings = analyze_call_chains(code, "app.py", {"openai"})
        assert len(findings) >= 1
        f = findings[0]
        assert f.pattern == "conditional_branching"
        assert f.ai_framework == "openai"
        assert f.severity == "critical"
        assert f.ai_call_line == 2
        assert f.decision_line == 3

    def test_no_ai_in_condition(self):
        code = """\
import openai
result = openai.chat.completions.create(model="gpt-4", messages=[])
x = 42
if x > 10:
    print("yes")
"""
        findings = analyze_call_chains(code, "app.py", {"openai"})
        assert not any(f.pattern == "conditional_branching" for f in findings)


class TestDatabasePersistence:
    """Detect AI output written to databases."""

    def test_sqlalchemy_add(self):
        code = """\
import openai
prediction = openai.chat.completions.create(model="gpt-4", messages=[])
session.add(prediction)
"""
        findings = analyze_call_chains(code, "app.py", {"openai"})
        db_findings = [f for f in findings if f.pattern == "database_persistence"]
        assert len(db_findings) >= 1
        assert db_findings[0].severity == "critical"

    def test_django_create(self):
        code = """\
import anthropic
result = anthropic.messages.create(model="claude-3", messages=[])
MyModel.objects.create(data=result)
"""
        findings = analyze_call_chains(code, "views.py", {"anthropic"})
        db_findings = [f for f in findings if f.pattern == "database_persistence"]
        assert len(db_findings) >= 1

    def test_no_db_write(self):
        code = """\
import openai
result = openai.chat.completions.create(model="gpt-4", messages=[])
print(result)
"""
        findings = analyze_call_chains(code, "app.py", {"openai"})
        db_findings = [f for f in findings if f.pattern == "database_persistence"]
        assert len(db_findings) == 0


class TestDownstreamApiCall:
    """Detect AI output sent to external services."""

    def test_requests_post(self):
        code = """\
import openai
result = openai.chat.completions.create(model="gpt-4", messages=[])
requests.post("https://api.example.com/notify", json=result)
"""
        findings = analyze_call_chains(code, "app.py", {"openai"})
        api_findings = [f for f in findings if f.pattern == "downstream_api_call"]
        assert len(api_findings) >= 1
        assert api_findings[0].severity == "warning"


class TestUIRendering:
    """Detect AI output rendered to users."""

    def test_json_response(self):
        code = """\
import openai
result = openai.chat.completions.create(model="gpt-4", messages=[])
JSONResponse(result)
"""
        findings = analyze_call_chains(code, "routes.py", {"openai"})
        ui_findings = [f for f in findings if f.pattern == "ui_rendering"]
        assert len(ui_findings) >= 1

    def test_return_ai_result(self):
        code = """\
import openai
def handler():
    result = openai.chat.completions.create(model="gpt-4", messages=[])
    return result
"""
        findings = analyze_call_chains(code, "handler.py", {"openai"})
        ui_findings = [f for f in findings if f.pattern == "ui_rendering"]
        assert len(ui_findings) >= 1


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_syntax_error_returns_empty(self):
        code = "def foo(\n  broken syntax here"
        findings = analyze_call_chains(code, "broken.py", {"openai"})
        assert findings == []

    def test_empty_ai_modules(self):
        code = "import openai\nresult = openai.create()\nif result: pass"
        findings = analyze_call_chains(code, "app.py", set())
        assert findings == []

    def test_empty_content(self):
        findings = analyze_call_chains("", "empty.py", {"openai"})
        assert findings == []

    def test_await_pattern(self):
        code = """\
import openai
async def handler():
    result = await openai.chat.completions.create(model="gpt-4", messages=[])
    if result:
        pass
"""
        findings = analyze_call_chains(code, "app.py", {"openai"})
        cond_findings = [f for f in findings if f.pattern == "conditional_branching"]
        assert len(cond_findings) >= 1

    def test_multiple_patterns_same_file(self):
        code = """\
import openai
result = openai.chat.completions.create(model="gpt-4", messages=[])
if result.score > 0.5:
    session.add(result)
    requests.post("https://api.example.com", json=result)
"""
        findings = analyze_call_chains(code, "app.py", {"openai"})
        patterns = {f.pattern for f in findings}
        assert "conditional_branching" in patterns
        assert "database_persistence" in patterns
        assert "downstream_api_call" in patterns
