"""
Tests for the PDF processing and chapter detection pipeline.

Covers:
  - PDF text extraction
  - Chapter detection (regex-based)
  - Chapter detection (TOC-based)
  - PDFs with no detectable chapters (fallback)
  - Malformed / invalid inputs
  - Document API endpoint flow (upload → processing → GET detail)
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

import fitz  # PyMuPDF
import pytest
import httpx

from app.models.document import Chapter, ProcessingStatus
from app.services.pdf_service import PDFService, PDFExtractionError, PageText
from app.services.chapter_service import ChapterService


# ── Test fixtures: generate PDF files on the fly ────────────────────

TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "_fixtures"


def _make_fixture_dir():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def create_text_pdf(path: Path, pages: list[str], toc: list[tuple[int, str, int]] | None = None) -> Path:
    """
    Create a text-based PDF with the given page contents.
    Optionally set a TOC (bookmarks).
    """
    _make_fixture_dir()
    doc = fitz.open()
    for page_text in pages:
        page = doc.new_page(width=595, height=842)  # A4
        text_point = fitz.Point(72, 72)
        page.insert_text(text_point, page_text, fontsize=11)
    if toc:
        doc.set_toc(toc)
    doc.save(str(path))
    doc.close()
    return path


def create_image_only_pdf(path: Path) -> Path:
    """Create a PDF with a drawn rectangle but no selectable text."""
    _make_fixture_dir()
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(100, 100, 300, 300)
    page.draw_rect(rect, color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    doc.save(str(path))
    doc.close()
    return path


# ────────────────────────────────────────────────────────────────────
# Unit Tests: PDFService
# ────────────────────────────────────────────────────────────────────


class TestPDFServiceValidation:
    """Tests for file validation."""

    def test_nonexistent_file(self):
        with pytest.raises(PDFExtractionError, match="not found"):
            PDFService.validate_file(Path("definitely_not_real.pdf"))

    def test_non_pdf_extension(self, tmp_path):
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Hello")
        with pytest.raises(PDFExtractionError, match="Only PDF"):
            PDFService.validate_file(txt_file)

    def test_oversized_file(self, tmp_path):
        big_file = tmp_path / "huge.pdf"
        # Create a file just over 25 MB
        big_file.write_bytes(b"x" * (26 * 1024 * 1024))
        with pytest.raises(PDFExtractionError, match="25 MB"):
            PDFService.validate_file(big_file)

    def test_valid_file(self, tmp_path):
        pdf_path = create_text_pdf(
            tmp_path / "valid.pdf",
            ["This is a valid test page with enough content to pass the minimum threshold. " * 5],
        )
        PDFService.validate_file(pdf_path)  # Should not raise


class TestPDFServiceExtraction:
    """Tests for page-by-page text extraction."""

    def test_extract_pages_basic(self, tmp_path):
        pages_text = [
            "Page one content here. " * 10,
            "Page two content here. " * 10,
            "Page three content here. " * 10,
        ]
        pdf_path = create_text_pdf(tmp_path / "three_pages.pdf", pages_text)

        result = PDFService.extract_pages(pdf_path)

        assert len(result) == 3
        assert result[0].page_number == 1
        assert result[1].page_number == 2
        assert result[2].page_number == 3
        assert "Page one" in result[0].text
        assert "Page two" in result[1].text
        assert "Page three" in result[2].text

    def test_extract_preserves_page_numbers(self, tmp_path):
        pdf_path = create_text_pdf(
            tmp_path / "numbered.pdf",
            [f"Content of page {i+1}. " * 10 for i in range(5)],
        )
        result = PDFService.extract_pages(pdf_path)
        assert [p.page_number for p in result] == [1, 2, 3, 4, 5]

    def test_extract_image_only_pdf_raises(self, tmp_path):
        pdf_path = create_image_only_pdf(tmp_path / "image_only.pdf")
        with pytest.raises(PDFExtractionError, match="scanned or image-only"):
            PDFService.extract_pages(pdf_path)

    def test_get_page_count(self, tmp_path):
        pdf_path = create_text_pdf(
            tmp_path / "count.pdf",
            ["Content. " * 20] * 7,
        )
        assert PDFService.get_page_count(pdf_path) == 7

    def test_extract_toc(self, tmp_path):
        toc = [
            [1, "Introduction", 1],
            [1, "Main Content", 3],
            [1, "Conclusion", 5],
        ]
        pdf_path = create_text_pdf(
            tmp_path / "with_toc.pdf",
            ["Content. " * 20] * 6,
            toc=toc,
        )
        result = PDFService.extract_toc(pdf_path)
        assert len(result) == 3
        assert result[0] == (1, "Introduction", 1)
        assert result[1] == (1, "Main Content", 3)
        assert result[2] == (1, "Conclusion", 5)


# ────────────────────────────────────────────────────────────────────
# Unit Tests: ChapterService
# ────────────────────────────────────────────────────────────────────


class TestChapterDetectionRegex:
    """Tests for regex-based chapter heading detection."""

    def test_standard_chapter_headings(self):
        pages = [
            PageText(1, "Chapter 1: Introduction to AI\nSome intro text here."),
            PageText(2, "More intro text. Concepts and definitions."),
            PageText(3, "Chapter 2: AI Project Cycle\nProject phases explained."),
            PageText(4, "Planning, collection, modelling steps."),
            PageText(5, "Chapter 3: Machine Intelligence\nML and DL concepts."),
            PageText(6, "Neural networks and training data."),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=None)

        assert len(chapters) == 3
        assert chapters[0].chapter_number == 1
        assert chapters[0].chapter_title == "Introduction to AI"
        assert chapters[0].start_page == 1
        assert chapters[0].end_page == 2

        assert chapters[1].chapter_number == 2
        assert chapters[1].chapter_title == "AI Project Cycle"
        assert chapters[1].start_page == 3
        assert chapters[1].end_page == 4

        assert chapters[2].chapter_number == 3
        assert chapters[2].chapter_title == "Machine Intelligence"
        assert chapters[2].start_page == 5
        assert chapters[2].end_page == 6

    def test_chapter_dash_separator(self):
        pages = [
            PageText(1, "Chapter 1 — Foundations\nText here."),
            PageText(2, "More text."),
            PageText(3, "Chapter 2 — Applications\nApps discussion."),
            PageText(4, "Final page."),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=None)
        assert len(chapters) == 2
        assert chapters[0].chapter_title == "Foundations"
        assert chapters[1].chapter_title == "Applications"



    def test_unit_headings(self):
        pages = [
            PageText(1, "Unit 1: Numbers\nBasic arithmetic."),
            PageText(2, "More numbers."),
            PageText(3, "Unit 2: Algebra\nEquations and variables."),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=None)
        assert len(chapters) == 2
        assert chapters[0].chapter_title == "Numbers"
        assert chapters[1].chapter_title == "Algebra"

    def test_skips_toc_dot_lines(self):
        """TOC entries like 'Machine Intelligence ......... 42' should NOT be
        detected as chapter headings."""
        pages = [
            PageText(1, "Table of Contents\nChapter 1 .......... 3\nChapter 2 .......... 10"),
            PageText(2, "Some other text before the real chapter."),
            PageText(3, "Chapter 1: Real Heading\nActual chapter content here."),
            PageText(10, "Chapter 2: Second Heading\nMore actual content."),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=None)
        assert len(chapters) == 2
        assert chapters[0].start_page == 3
        assert chapters[1].start_page == 10

    def test_science_syllabus_structure_roman_numerals(self):
        """Test the explicit detection of units with Roman numerals and skipping syllabus notes."""
        pages = [
            PageText(1, "CG 1 - Explores the world of matter\nC 1.1 - Describes classification\nCourse Structure\nNote for Teachers:"),
            PageText(2, "Unit I: Chemical Substances - Nature and Behaviour\nChemical Reactions..."),
            PageText(3, "Unit II: World of Living\nLife processes..."),
            PageText(4, "Unit III: Natural Phenomena\nFunctioning of a lens..."),
            PageText(5, "Unit IV: Effects of Current\nElectric current..."),
            PageText(6, "Unit V: Natural Resources\nOur environment...\nPracticals\nQuestion Paper Design"),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=None)
        assert len(chapters) == 5
        assert chapters[0].chapter_number == 1
        assert chapters[0].chapter_title == "Chemical Substances - Nature and Behaviour"
        assert chapters[1].chapter_number == 2
        assert chapters[1].chapter_title == "World of Living"
        assert chapters[2].chapter_number == 3
        assert chapters[2].chapter_title == "Natural Phenomena"
        assert chapters[3].chapter_number == 4
        assert chapters[3].chapter_title == "Effects of Current"
        assert chapters[4].chapter_number == 5
        assert chapters[4].chapter_title == "Natural Resources"



class TestChapterDetectionTOC:
    """Tests for TOC/bookmark-based chapter detection."""

    def test_toc_based_detection(self):
        pages = [PageText(i + 1, f"Content page {i+1}. " * 10) for i in range(20)]
        toc = [
            (1, "Chapter 1: Intro to AI", 1),
            (1, "Chapter 2: Project Cycle", 6),
            (1, "Chapter 3: Machine Intelligence", 11),
            (1, "Chapter 4: Cybersecurity", 16),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=toc)

        assert len(chapters) == 4
        assert chapters[0].chapter_title == "Chapter 1: Intro to AI"
        assert chapters[0].start_page == 1
        assert chapters[0].end_page == 5

        assert chapters[3].chapter_title == "Chapter 4: Cybersecurity"
        assert chapters[3].start_page == 16
        assert chapters[3].end_page == 20

    def test_toc_filters_front_matter(self):
        pages = [PageText(i + 1, f"Content. " * 20) for i in range(15)]
        toc = [
            (1, "Preface", 1),
            (1, "Acknowledgements", 2),
            (1, "Chapter One: Real Content", 3),
            (1, "Chapter Two: More Content", 8),
            (1, "Index", 14),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=toc)

        # Should only have the two real chapters
        assert len(chapters) == 2
        assert chapters[0].chapter_title == "Chapter One: Real Content"
        assert chapters[1].chapter_title == "Chapter Two: More Content"

    def test_toc_ignores_sub_levels(self):
        pages = [PageText(i + 1, f"Content. " * 20) for i in range(10)]
        toc = [
            (1, "Chapter 1", 1),
            (2, "Section 1.1", 2),
            (2, "Section 1.2", 3),
            (1, "Chapter 2", 5),
            (2, "Section 2.1", 6),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=toc)
        assert len(chapters) == 2
        assert chapters[0].chapter_title == "Chapter 1"
        assert chapters[1].chapter_title == "Chapter 2"


class TestChapterDetectionFallback:
    """Tests for documents with no detectable chapters."""

    def test_no_chapters_returns_full_document(self):
        pages = [
            PageText(1, "Some random text with no chapter headings at all."),
            PageText(2, "More random text. Just a continuous document."),
            PageText(3, "Final page of random content here."),
        ]
        chapters = ChapterService.detect_chapters(pages, toc=None)

        assert len(chapters) == 1
        assert chapters[0].chapter_number == 1
        assert chapters[0].chapter_title == "Full Document"
        assert chapters[0].start_page == 1
        assert chapters[0].end_page == 3

    def test_empty_pages_returns_empty(self):
        chapters = ChapterService.detect_chapters([], toc=None)
        assert chapters == []


# ── Fixtures for API tests ──────────────────────────────────────────


@pytest.fixture
def _patch_dirs(tmp_path):
    """Patch config paths to use a temporary directory for each test."""
    from app.core import config as config_module
    from app.services import document_store as ds_module

    original_data_dir = config_module.settings.DATA_DIR
    original_uploads_dir = config_module.settings.UPLOADS_DIR
    original_metadata_dir = ds_module._METADATA_DIR
    original_metadata_file = ds_module._METADATA_FILE

    test_data = tmp_path / "data"
    test_uploads = test_data / "uploads"
    test_uploads.mkdir(parents=True)

    config_module.settings.DATA_DIR = test_data
    config_module.settings.UPLOADS_DIR = test_uploads
    ds_module._METADATA_DIR = test_data / "metadata"
    ds_module._METADATA_FILE = ds_module._METADATA_DIR / "documents.json"

    yield

    config_module.settings.DATA_DIR = original_data_dir
    config_module.settings.UPLOADS_DIR = original_uploads_dir
    ds_module._METADATA_DIR = original_metadata_dir
    ds_module._METADATA_FILE = original_metadata_file


def _make_api_test_pdf(tmp_path: Path, name: str = "test.pdf") -> Path:
    pages = [
        "Chapter 1: Introduction to AI\nArtificial intelligence is the simulation of human intelligence. " * 5,
        "AI can be applied to many domains including healthcare and education. " * 5,
        "Chapter 2: Machine Learning\nMachine learning is a subset of AI that learns from data. " * 5,
        "Supervised and unsupervised learning are the two main categories. " * 5,
        "Chapter 3: Deep Learning\nDeep learning uses neural networks with multiple layers. " * 5,
    ]
    return create_text_pdf(tmp_path / name, pages)


# ── API Integration Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_success(_patch_dirs, tmp_path):
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_path = _make_api_test_pdf(tmp_path)
        with open(pdf_path, "rb") as f:
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("AI_Textbook.pdf", f, "application/pdf")},
                data={"class_name": "10", "subject": "Artificial Intelligence"},
            )
        assert response.status_code == 201
        body = response.json()
        assert body["document_name"] == "AI_Textbook.pdf"
        assert body["processing_status"] == "uploaded"
        assert body["document_id"].startswith("doc_")


@pytest.mark.asyncio
async def test_upload_invalid_class(_patch_dirs, tmp_path):
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_path = _make_api_test_pdf(tmp_path)
        with open(pdf_path, "rb") as f:
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"class_name": "15", "subject": "Math"},
            )
        assert response.status_code == 400
        assert "Invalid class" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_subject(_patch_dirs, tmp_path):
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_path = _make_api_test_pdf(tmp_path)
        with open(pdf_path, "rb") as f:
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"class_name": "10", "subject": "   "},
            )
        assert response.status_code == 400
        assert "Subject" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_non_pdf_rejected(_patch_dirs, tmp_path):
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Not a PDF")
        with open(txt_file, "rb") as f:
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("notes.txt", f, "text/plain")},
                data={"class_name": "10", "subject": "English"},
            )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file_rejected(_patch_dirs, tmp_path):
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")
        with open(empty_pdf, "rb") as f:
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("empty.pdf", f, "application/pdf")},
                data={"class_name": "10", "subject": "Science"},
            )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_documents_empty(_patch_dirs):
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/documents")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_get_document_not_found(_patch_dirs):
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/documents/nonexistent_id")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_full_upload_and_processing_flow(_patch_dirs, tmp_path):
    """
    End-to-end: upload PDF → background text extraction → chapter detection
    → verify document detail with chapters via GET.
    """
    import asyncio
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_path = _make_api_test_pdf(tmp_path)

        # Upload
        with open(pdf_path, "rb") as f:
            upload_resp = await client.post(
                "/api/documents/upload",
                files={"file": ("AI_Textbook.pdf", f, "application/pdf")},
                data={"class_name": "10", "subject": "Artificial Intelligence"},
            )
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["document_id"]

        # Wait for background processing to complete
        for _ in range(100):
            detail_resp = await client.get(f"/api/documents/{doc_id}")
            status = detail_resp.json()["processing_status"]
            if status in ("processed", "failed"):
                break
            await asyncio.sleep(0.1)

        detail = detail_resp.json()
        assert detail["processing_status"] == "processed", (
            f"Processing failed: {detail.get('error_message')}"
        )
        assert detail["document_name"] == "AI_Textbook.pdf"
        assert detail["class_name"] == "10"
        assert detail["subject"] == "Artificial Intelligence"
        assert detail["page_count"] == 5

        # Verify detected chapters
        chapters = detail["chapters"]
        assert len(chapters) == 3

        assert chapters[0]["chapter_number"] == 1
        assert chapters[0]["chapter_title"] == "Introduction to AI"
        assert chapters[0]["start_page"] == 1

        assert chapters[1]["chapter_number"] == 2
        assert chapters[1]["chapter_title"] == "Machine Learning"

        assert chapters[2]["chapter_number"] == 3
        assert chapters[2]["chapter_title"] == "Deep Learning"
        assert chapters[2]["end_page"] == 5

        # Verify list endpoint
        list_resp = await client.get("/api/documents")
        assert list_resp.status_code == 200
        docs = list_resp.json()
        assert len(docs) == 1
        assert docs[0]["document_id"] == doc_id
        assert docs[0]["chapter_count"] == 3
        assert docs[0]["page_count"] == 5


@pytest.mark.asyncio
async def test_health_endpoint_still_works(_patch_dirs):
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

