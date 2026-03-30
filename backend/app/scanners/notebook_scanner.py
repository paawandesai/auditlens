"""Jupyter notebook scanner — extract code and markdown from .ipynb files.

Jupyter notebooks are JSON files containing an array of cells. Each cell
has a type ("code" or "markdown") and a source (list of strings).

This module extracts:
- Code cells → concatenated Python source for import scanning
- Markdown cells → concatenated text for content/keyword analysis

No new dependencies — uses stdlib json only.
"""

from __future__ import annotations

import json


def select_notebook_files(file_paths: list[str], max_files: int = 10) -> list[str]:
    """Select .ipynb files from the file tree, prioritizing relevant directories.

    Args:
        file_paths: All file paths in the repository.
        max_files: Maximum notebooks to return.

    Returns:
        List of .ipynb file paths, capped at max_files.
    """
    notebooks = [p for p in file_paths if p.lower().endswith(".ipynb")]
    if not notebooks:
        return []

    # Prioritize: root > notebooks/ > src/ > examples/ > other
    def priority(p: str) -> int:
        if "/" not in p:
            return 0
        top_dir = p.split("/")[0].lower()
        if top_dir in ("notebooks", "notebook", "nbs"):
            return 1
        if top_dir in ("src", "lib", "app"):
            return 2
        if top_dir in ("examples", "demos", "tutorials"):
            return 3
        return 4

    notebooks.sort(key=priority)
    return notebooks[:max_files]


def extract_notebook_cells(content: str) -> tuple[str, str]:
    """Parse a .ipynb JSON file and extract code and markdown content.

    Args:
        content: Raw JSON string of the notebook file.

    Returns:
        Tuple of (code_source, markdown_source):
        - code_source: All code cells concatenated with newlines
        - markdown_source: All markdown cells concatenated with newlines
    """
    try:
        nb = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return "", ""

    cells = nb.get("cells", [])
    if not cells:
        return "", ""

    code_lines: list[str] = []
    markdown_lines: list[str] = []

    for cell in cells:
        cell_type = cell.get("cell_type", "")
        source = cell.get("source", [])

        # Source can be a list of strings or a single string
        if isinstance(source, list):
            text = "".join(source)
        elif isinstance(source, str):
            text = source
        else:
            continue

        if cell_type == "code":
            code_lines.append(text)
        elif cell_type == "markdown":
            markdown_lines.append(text)

    return "\n".join(code_lines), "\n".join(markdown_lines)
