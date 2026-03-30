"""File processor — extract plain text from uploaded compliance documents.

Supports PDF, DOCX, MD, and TXT files. All processing is server-side.
No external API calls — pure local text extraction.

Security:
- File type validated before processing
- File size capped at MAX_FILE_SIZE
- Text output truncated to MAX_TEXT_LENGTH
- No file content stored in memory after extraction
"""

from __future__ import annotations

import io

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/markdown",
    "text/plain",
}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_TEXT_LENGTH = 100_000  # ~50 pages of text


class FileProcessingError(Exception):
    """Raised when file processing fails."""


def validate_file(filename: str, content_type: str, size: int) -> None:
    """Validate file type and size before processing.

    Raises FileProcessingError if validation fails.
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise FileProcessingError(
            f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if size > MAX_FILE_SIZE:
        raise FileProcessingError(
            f"File too large: {size / 1024 / 1024:.1f}MB. Maximum: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from a file based on its extension.

    Args:
        file_bytes: Raw file content.
        filename: Original filename (used for extension detection).

    Returns:
        Extracted text, truncated to MAX_TEXT_LENGTH.

    Raises:
        FileProcessingError: If extraction fails.
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext == ".pdf":
            text = _extract_pdf(file_bytes)
        elif ext == ".docx":
            text = _extract_docx(file_bytes)
        elif ext in (".md", ".txt"):
            text = file_bytes.decode("utf-8", errors="replace")
        else:
            raise FileProcessingError(f"Cannot extract text from {ext} files")
    except FileProcessingError:
        raise
    except Exception as exc:
        raise FileProcessingError(f"Failed to extract text from {filename}: {exc}") from exc

    # Truncate to limit
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + f"\n\n[Truncated — showing first {MAX_TEXT_LENGTH:,} characters]"

    return text


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    from PyPDF2 import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages: list[str] = []

    for page in reader.pages[:50]:  # Cap at 50 pages
        text = page.extract_text()
        if text:
            pages.append(text)

    if not pages:
        raise FileProcessingError("PDF contains no extractable text (may be scanned/image-only)")

    return "\n\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    tables_text = []
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                tables_text.append(row_text)

    if not paragraphs and not tables_text:
        raise FileProcessingError("DOCX contains no extractable text")

    return "\n".join(paragraphs + tables_text)
