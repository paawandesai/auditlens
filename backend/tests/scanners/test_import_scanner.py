"""Tests for import_scanner — Python import-based framework detection."""

from __future__ import annotations

from app.scanners.import_scanner import (
    merge_frameworks,
    scan_python_imports,
    scan_python_imports_ast,
    select_python_files,
)
from app.schemas.scanner import DetectedFramework


class TestScanPythonImports:
    """Tests for regex-based Python import scanning."""

    def test_empty_content_no_frameworks(self):
        assert scan_python_imports("") == []

    def test_import_torch(self):
        content = "import torch\nmodel = torch.nn.Linear(10, 5)"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "torch" in names

    def test_from_sklearn_import(self):
        content = "from sklearn.ensemble import RandomForestClassifier"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "scikit-learn" in names

    def test_import_tensorflow(self):
        content = "import tensorflow as tf"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "tensorflow" in names

    def test_from_transformers_import(self):
        content = "from transformers import AutoTokenizer, AutoModel"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "transformers" in names

    def test_import_openai(self):
        content = "import openai\nclient = openai.OpenAI()"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "openai" in names

    def test_import_pandas(self):
        content = "import pandas as pd\ndf = pd.DataFrame()"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "pandas" in names

    def test_non_ai_imports_ignored(self):
        content = "import os\nimport sys\nfrom pathlib import Path\nimport json"
        assert scan_python_imports(content) == []

    def test_multiple_ai_imports(self):
        content = """
import torch
from sklearn.model_selection import train_test_split
import openai
from transformers import pipeline
"""
        results = scan_python_imports(content)
        names = {r.name for r in results}
        assert "torch" in names
        assert "scikit-learn" in names
        assert "openai" in names
        assert "transformers" in names

    def test_confidence_reduced_from_manifest(self):
        """Import-detected frameworks should have lower confidence."""
        content = "import torch"
        results = scan_python_imports(content)
        torch_fw = next(r for r in results if r.name == "torch")
        # Original confidence is 0.95, minus 0.15 penalty ≈ 0.80
        assert abs(torch_fw.confidence - 0.80) < 0.01

    def test_deduplication(self):
        content = """
import torch
import torch.nn
from torch.optim import Adam
"""
        results = scan_python_imports(content)
        torch_matches = [r for r in results if r.name == "torch"]
        assert len(torch_matches) == 1

    def test_from_deep_import(self):
        content = "from sklearn.preprocessing import StandardScaler"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "scikit-learn" in names

    def test_cv2_maps_to_opencv(self):
        content = "import cv2"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "opencv-python" in names

    def test_commented_imports_match(self):
        """Regex matches lines starting with import — comments won't match."""
        content = "# import torch\nimport os"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "torch" not in names

    def test_langchain_detected(self):
        content = "from langchain.chains import LLMChain"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "langchain" in names

    def test_fairlearn_detected(self):
        content = "from fairlearn.metrics import MetricFrame"
        results = scan_python_imports(content)
        names = [r.name for r in results]
        assert "fairlearn" in names


class TestSelectPythonFiles:
    """Tests for selecting which .py files to scan."""

    def test_empty_tree(self):
        assert select_python_files([]) == []

    def test_main_py_selected(self):
        paths = ["README.md", "main.py", "setup.py"]
        result = select_python_files(paths)
        assert "main.py" in result

    def test_model_files_selected(self):
        paths = ["src/model.py", "src/utils.py"]
        result = select_python_files(paths)
        assert "src/model.py" in result
        assert "src/utils.py" not in result

    def test_train_files_selected(self):
        paths = ["scripts/train_model.py", "scripts/deploy.py"]
        result = select_python_files(paths)
        assert "scripts/train_model.py" in result

    def test_pipeline_files_selected(self):
        paths = ["ml/pipeline.py"]
        result = select_python_files(paths)
        assert "ml/pipeline.py" in result

    def test_max_files_capped(self):
        paths = [
            "main.py", "app.py", "run.py", "server.py", "api.py",
            "model.py", "model2.py", "predict.py",
            "train.py", "pipeline.py", "inference.py",
            "agent.py", "llm.py", "chat.py",
            "routes/users.py", "routers/items.py",
            "extra1.py", "extra2.py",
        ]
        result = select_python_files(paths)
        assert len(result) <= 30

    def test_non_python_files_excluded(self):
        paths = ["model.js", "train.ts", "pipeline.go"]
        assert select_python_files(paths) == []

    def test_inference_files_selected(self):
        paths = ["src/inference.py", "src/config.py"]
        result = select_python_files(paths)
        assert "src/inference.py" in result


class TestMergeFrameworks:
    """Tests for merging manifest and import-detected frameworks."""

    def test_no_overlap(self):
        manifest = [DetectedFramework(name="torch", confidence=0.95, hr_relevance_score=0.5)]
        imports = [DetectedFramework(name="openai", confidence=0.75, hr_relevance_score=0.6)]
        merged = merge_frameworks(manifest, imports)
        names = {f.name for f in merged}
        assert names == {"torch", "openai"}

    def test_overlap_keeps_higher_confidence(self):
        manifest = [DetectedFramework(name="torch", confidence=0.95, hr_relevance_score=0.5)]
        imports = [DetectedFramework(name="torch", confidence=0.80, hr_relevance_score=0.5)]
        merged = merge_frameworks(manifest, imports)
        assert len(merged) == 1
        assert merged[0].confidence == 0.95  # manifest wins

    def test_empty_inputs(self):
        assert merge_frameworks([], []) == []

    def test_import_only(self):
        imports = [DetectedFramework(name="torch", confidence=0.80, hr_relevance_score=0.5)]
        merged = merge_frameworks([], imports)
        assert len(merged) == 1
        assert merged[0].name == "torch"


class TestScanPythonImportsAst:
    """Tests for AST-based Python import scanning with line numbers."""

    def test_ast_detects_import(self):
        code = "import torch\nmodel = torch.nn.Linear(10, 5)"
        frameworks, imports = scan_python_imports_ast(code, "model.py")
        assert any(f.name == "torch" for f in frameworks)
        assert len(imports) >= 1
        assert imports[0].line == 1
        assert imports[0].file == "model.py"

    def test_ast_detects_from_import(self):
        code = "from sklearn.ensemble import RandomForestClassifier"
        frameworks, imports = scan_python_imports_ast(code, "train.py")
        assert any(f.name == "scikit-learn" for f in frameworks)
        assert imports[0].module == "sklearn.ensemble"
        assert imports[0].line == 1

    def test_ast_fallback_on_syntax_error(self):
        code = "import torch\ndef broken(\n  invalid syntax"
        # Should fallback to regex, still detect torch
        frameworks, imports = scan_python_imports_ast(code, "broken.py")
        assert any(f.name == "torch" for f in frameworks)
        # No imports from AST (fell back to regex which doesn't produce them)
        assert imports == []

    def test_ast_multiple_imports(self):
        code = """\
import openai
from sklearn.ensemble import RandomForestClassifier
import torch
"""
        frameworks, imports = scan_python_imports_ast(code, "pipeline.py")
        names = {f.name for f in frameworks}
        assert "openai" in names
        assert "scikit-learn" in names
        assert "torch" in names
        assert len(imports) == 3
        # Verify line numbers
        lines = {i.line for i in imports}
        assert lines == {1, 2, 3}

    def test_ast_deduplication(self):
        code = "import torch\nimport torch\n"
        frameworks, imports = scan_python_imports_ast(code, "dup.py")
        assert len(frameworks) == 1

    def test_ast_empty_content(self):
        frameworks, imports = scan_python_imports_ast("", "empty.py")
        assert frameworks == []
        assert imports == []

    def test_ast_col_offset(self):
        code = "import openai\n"
        _, imports = scan_python_imports_ast(code, "app.py")
        assert len(imports) >= 1
        assert imports[0].col == 0
