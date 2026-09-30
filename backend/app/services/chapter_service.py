"""
Chapter detection service.

Implements a multi-strategy pipeline to identify chapter boundaries
in extracted PDF text, as specified in PRD Section 7 (Feature 3, Step 2).

Strategy order:
  1. PDF outline / bookmarks (PyMuPDF TOC)
  2. Regex-based heading detection on page text
  3. (Future) LLM-assisted fallback for poorly structured PDFs

Each chapter is returned with:
  chapter_number, chapter_title, start_page, end_page
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.document import Chapter
from app.services.pdf_service import PageText


@dataclass
class _RawChapterHit:
    """Intermediate representation of a detected chapter heading."""
    title: str
    page_number: int
    detected_number: int | None = None  # The chapter number parsed from text, if any


# ────────────────────────────────────────────────────────────────────
# Regex patterns for structural chapter detection (ordered by specificity)
# ────────────────────────────────────────────────────────────────────

_CHAPTER_PATTERNS: list[re.Pattern] = [
    # "Chapter 3: Machine Intelligence" / "Chapter 3 — Machine Intelligence"
    re.compile(
        r"^\s*chapter\s+(\d+)\s*[:\-–—.]\s*(.+)",
        re.IGNORECASE,
    ),
    # "Chapter 3" alone on a line
    re.compile(
        r"^\s*chapter\s+(\d+)\s*$",
        re.IGNORECASE,
    ),
    # "CHAPTER 3  MACHINE INTELLIGENCE" (all-caps, space separated)
    re.compile(
        r"^\s*CHAPTER\s+(\d+)\s+([A-Z][A-Z\s]+)$",
    ),
    # "Unit 3: ..." / "Unit 3 — ..."
    re.compile(
        r"^\s*unit\s+(\d+)\s*[:\-–—.]\s*(.+)",
        re.IGNORECASE,
    ),
    # "3. Machine Intelligence" (number-dot at start of line, title follows)
    re.compile(
        r"^\s*(\d{1,2})\.\s+([A-Z][A-Za-z\s]{4,})",
    ),
]

# Lines that look like TOC entries rather than actual chapter headings
_TOC_LINE_PATTERN = re.compile(
    r"\.\s*\.+\s*\d+\s*$"  # "Machine Intelligence ......... 42"
)


class ChapterService:
    """Detects chapter boundaries from extracted PDF pages and/or TOC."""

    # ── Public API ──────────────────────────────────────────────────

    @classmethod
    def detect_chapters(
        cls,
        pages: list[PageText],
        toc: list[tuple[int, str, int]] | None = None,
    ) -> list[Chapter]:
        """
        Run the chapter detection pipeline and return a list of Chapter models.

        Tries strategies in order:
          1. PDF built-in TOC/bookmarks (if present and has chapter-like entries)
          2. Regex heading detection on page text

        If neither yields results, returns a single chapter spanning the
        entire document so the pipeline can still proceed.
        """
        total_pages = len(pages) if pages else 0
        if total_pages == 0:
            return []

        # Strategy 1: PDF built-in TOC
        if toc:
            chapters = cls._from_toc(toc, total_pages)
            if chapters:
                return chapters

        # Strategy 2: Regex heading detection
        chapters = cls._from_regex(pages)
        if chapters:
            return cls._finalize(chapters, total_pages)

        # Fallback: treat entire document as one chapter
        return [
            Chapter(
                chapter_number=1,
                chapter_title="Full Document",
                start_page=1,
                end_page=total_pages,
            )
        ]

    # ── Strategy 1: PDF TOC / Bookmarks ─────────────────────────────

    @classmethod
    def _from_toc(
        cls,
        toc: list[tuple[int, str, int]],
        total_pages: int,
    ) -> list[Chapter]:
        """
        Build chapter list from PyMuPDF's built-in TOC.

        Only uses top-level entries (level == 1).
        Filters out entries that look like front-matter
        (preface, acknowledgements, index, etc.).
        """
        top_level = [
            (title.strip(), page)
            for level, title, page in toc
            if level == 1 and page >= 1 and title.strip()
        ]

        if len(top_level) < 2:
            return []

        # Filter out common non-chapter entries
        filtered = [
            (title, page)
            for title, page in top_level
            if not cls._is_front_or_back_matter(title)
        ]

        if len(filtered) < 2:
            return []

        chapters: list[Chapter] = []
        for idx, (title, start_page) in enumerate(filtered):
            if idx + 1 < len(filtered):
                end_page = filtered[idx + 1][1] - 1
            else:
                end_page = total_pages

            # Ensure end_page >= start_page
            end_page = max(end_page, start_page)

            chapters.append(
                Chapter(
                    chapter_number=idx + 1,
                    chapter_title=cls._clean_title(title),
                    start_page=start_page,
                    end_page=end_page,
                )
            )

        return chapters

    # ── Strategy 2: Regex heading detection ──────────────────────────

    @classmethod
    def _from_regex(cls, pages: list[PageText]) -> list[_RawChapterHit]:
        """
        Scan every page for lines matching chapter heading patterns.

        Returns a list of raw chapter hits (unfinalized — no end_page yet).
        """
        hits: list[_RawChapterHit] = []
        seen_titles: set[str] = set()

        for page in pages:
            if not page.text:
                continue

            for line in page.text.split("\n"):
                line_stripped = line.strip()
                if not line_stripped or len(line_stripped) < 3:
                    continue

                # Skip lines that look like TOC entries (dots + page number)
                if _TOC_LINE_PATTERN.search(line_stripped):
                    continue

                hit = cls._match_chapter_line(line_stripped, page.page_number)
                if hit:
                    # Deduplicate (same title may appear in headers/footers)
                    key = hit.title.lower()
                    if key not in seen_titles:
                        seen_titles.add(key)
                        hits.append(hit)

        return hits

    @classmethod
    def _match_chapter_line(
        cls, line: str, page_number: int
    ) -> _RawChapterHit | None:
        """Test a single line against all chapter patterns."""
        for pattern in _CHAPTER_PATTERNS:
            m = pattern.match(line)
            if m:
                groups = m.groups()
                if len(groups) == 2:
                    num_str, title = groups
                    return _RawChapterHit(
                        title=cls._clean_title(title),
                        page_number=page_number,
                        detected_number=int(num_str),
                    )
                elif len(groups) == 1:
                    num_str = groups[0]
                    return _RawChapterHit(
                        title=f"Chapter {num_str}",
                        page_number=page_number,
                        detected_number=int(num_str),
                    )
        return None

    # ── Helpers ──────────────────────────────────────────────────────

    @classmethod
    def _finalize(
        cls, hits: list[_RawChapterHit], total_pages: int
    ) -> list[Chapter]:
        """
        Convert raw chapter hits into Chapter models with proper
        end_page values and sequential numbering.
        """
        # Sort by page number, then by detected number
        hits.sort(key=lambda h: (h.page_number, h.detected_number or 0))

        chapters: list[Chapter] = []
        for idx, hit in enumerate(hits):
            start_page = hit.page_number

            if idx + 1 < len(hits):
                end_page = hits[idx + 1].page_number - 1
            else:
                end_page = total_pages

            end_page = max(end_page, start_page)

            chapters.append(
                Chapter(
                    chapter_number=hit.detected_number or (idx + 1),
                    chapter_title=hit.title,
                    start_page=start_page,
                    end_page=end_page,
                )
            )

        return chapters

    @staticmethod
    def _clean_title(title: str) -> str:
        """Normalize whitespace and strip trailing punctuation from a title."""
        title = re.sub(r"\s+", " ", title).strip()
        title = title.rstrip(".:;-–—")
        return title.strip()

    @staticmethod
    def _is_front_or_back_matter(title: str) -> bool:
        """Return True if a TOC entry looks like non-chapter material."""
        skip_words = {
            "preface", "foreword", "acknowledgement", "acknowledgements",
            "contents", "table of contents", "index", "glossary",
            "bibliography", "references", "appendix", "introduction",
            "about the author", "about the book", "copyright",
            "dedication", "list of figures", "list of tables",
        }
        return title.strip().lower() in skip_words
