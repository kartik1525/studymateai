"""
PDF text extraction service using PyMuPDF (fitz).

Extracts text page-by-page, preserving page numbers.
Validates that the PDF contains extractable text content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz  # PyMuPDF


@dataclass
class PageText:
    """A single page of extracted text."""
    page_number: int  # 1-indexed
    text: str


class PDFExtractionError(Exception):
    """Raised when PDF extraction fails."""
    pass


class PDFService:
    """Handles PDF validation and page-by-page text extraction."""

    # Minimum total character count across all pages to consider a PDF text-based
    MIN_TEXT_CHARS = 100

    @staticmethod
    def validate_file(file_path: Path) -> None:
        """
        Validate that a file exists, is a PDF, and is within size limits.

        Raises PDFExtractionError on any validation failure.
        """
        if not file_path.exists():
            raise PDFExtractionError(f"File not found: {file_path.name}")

        if file_path.suffix.lower() != ".pdf":
            raise PDFExtractionError("Only PDF files are supported.")

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > 25:
            raise PDFExtractionError(
                f"File size ({size_mb:.1f} MB) exceeds the 25 MB limit."
            )

    @staticmethod
    def extract_pages(file_path: Path) -> list[PageText]:
        """
        Extract text from every page of a PDF.

        Returns a list of PageText objects with 1-indexed page numbers.
        Raises PDFExtractionError if the file cannot be opened or
        contains no extractable text (likely a scanned/image-only PDF).
        """
        try:
            doc = fitz.open(str(file_path))
        except Exception as exc:
            raise PDFExtractionError(f"Cannot open PDF: {exc}") from exc

        pages: list[PageText] = []
        total_chars = 0

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                text = page.get_text("text") or ""
                text = text.strip()
                total_chars += len(text)
                pages.append(PageText(page_number=page_idx + 1, text=text))
        finally:
            doc.close()

        if total_chars < PDFService.MIN_TEXT_CHARS:
            raise PDFExtractionError(
                "This PDF appears to be scanned or image-only. "
                "StudyMate AI currently supports text-based PDFs. "
                "Please upload a PDF with selectable text."
            )

        return pages

    @staticmethod
    def get_page_count(file_path: Path) -> int:
        """Return the total number of pages without extracting all text."""
        try:
            doc = fitz.open(str(file_path))
            count = len(doc)
            doc.close()
            return count
        except Exception as exc:
            raise PDFExtractionError(f"Cannot open PDF: {exc}") from exc

    @staticmethod
    def extract_toc(file_path: Path) -> list[tuple[int, str, int]]:
        """
        Extract the PDF's built-in table of contents / outline / bookmarks.

        Returns a list of (level, title, page_number) tuples.
        Page numbers are 1-indexed.
        """
        try:
            doc = fitz.open(str(file_path))
            toc = doc.get_toc()  # Returns [[level, title, page], ...]
            doc.close()
            return [(level, title, page) for level, title, page in toc]
        except Exception:
            return []
