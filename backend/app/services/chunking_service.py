"""
Semantic chunking service for document text.

Splits extracted page text into chunks that:
  - Never cross chapter boundaries
  - Preserve page-number attribution
  - Use configurable chunk size and overlap
  - Produce chunks suitable for embedding and similarity search

PRD Section 7, Step 3 — "Split chapter content into semantic chunks."
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from app.models.document import Chapter
from app.services.pdf_service import PageText

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────

DEFAULT_CHUNK_SIZE = 800       # target characters per chunk
DEFAULT_CHUNK_OVERLAP = 150    # overlap characters between consecutive chunks
MIN_CHUNK_SIZE = 80            # discard chunks shorter than this


@dataclass
class ChunkConfig:
    """Configurable chunking parameters."""
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    min_chunk_size: int = MIN_CHUNK_SIZE


@dataclass
class TextChunk:
    """A single text chunk ready for embedding, with full metadata."""
    chunk_id: str
    text: str
    document_id: str
    document_name: str
    class_name: str
    subject: str
    chapter_number: int
    chapter_title: str
    page: int                   # Primary page this chunk starts on


class ChunkingService:
    """Splits document text into chapter-bounded semantic chunks."""

    @classmethod
    def chunk_document(
        cls,
        pages: list[PageText],
        chapters: list[Chapter],
        document_id: str,
        document_name: str,
        class_name: str,
        subject: str,
        config: ChunkConfig | None = None,
    ) -> list[TextChunk]:
        """
        Main entry point: produce all chunks for a document.

        For each chapter, collects the pages in its range, concatenates
        the text (preserving page markers internally), then splits into
        overlapping chunks of the configured size.
        """
        if config is None:
            config = ChunkConfig()

        all_chunks: list[TextChunk] = []

        for chapter in chapters:
            chapter_chunks = cls._chunk_chapter(
                pages=pages,
                chapter=chapter,
                document_id=document_id,
                document_name=document_name,
                class_name=class_name,
                subject=subject,
                config=config,
            )
            all_chunks.extend(chapter_chunks)

        logger.info(
            "Chunked document %s (%s): %d chapters -> %d chunks "
            "(chunk_size=%d, overlap=%d)",
            document_id, document_name, len(chapters),
            len(all_chunks), config.chunk_size, config.chunk_overlap,
        )

        return all_chunks

    # ── Internal ────────────────────────────────────────────────────

    @classmethod
    def _chunk_chapter(
        cls,
        pages: list[PageText],
        chapter: Chapter,
        document_id: str,
        document_name: str,
        class_name: str,
        subject: str,
        config: ChunkConfig,
    ) -> list[TextChunk]:
        """
        Build page-annotated segments for one chapter, then split into
        overlapping chunks.
        """
        # Collect (page_number, text) pairs for pages in this chapter's range
        page_segments: list[tuple[int, str]] = []
        for page in pages:
            if chapter.start_page <= page.page_number <= chapter.end_page:
                text = page.text.strip()
                if text:
                    page_segments.append((page.page_number, text))

        if not page_segments:
            return []

        # Build a single text stream with embedded page markers that we can
        # later use to attribute pages.  We join with double-newline so
        # paragraph breaks are preserved.
        #
        # Instead of embedding invisible markers, we track (offset, page_num)
        # to know which page each character offset belongs to.
        offset_to_page: list[tuple[int, int]] = []  # (start_offset, page_number)
        combined_parts: list[str] = []
        current_offset = 0

        for page_num, text in page_segments:
            offset_to_page.append((current_offset, page_num))
            combined_parts.append(text)
            current_offset += len(text) + 2  # +2 for the "\n\n" separator

        combined_text = "\n\n".join(combined_parts)

        # Split into overlapping windows
        raw_windows = cls._split_with_overlap(
            combined_text, config.chunk_size, config.chunk_overlap
        )

        chunks: list[TextChunk] = []
        for start_offset, window_text in raw_windows:
            window_text = window_text.strip()
            if len(window_text) < config.min_chunk_size:
                continue

            # Determine the primary page for this chunk
            primary_page = cls._page_for_offset(offset_to_page, start_offset)

            chunk = TextChunk(
                chunk_id=f"chunk_{uuid.uuid4().hex[:10]}",
                text=window_text,
                document_id=document_id,
                document_name=document_name,
                class_name=class_name,
                subject=subject,
                chapter_number=chapter.chapter_number,
                chapter_title=chapter.chapter_title,
                page=primary_page,
            )
            chunks.append(chunk)

        return chunks

    @classmethod
    def _split_with_overlap(
        cls, text: str, chunk_size: int, overlap: int
    ) -> list[tuple[int, str]]:
        """
        Split text into overlapping windows.

        Tries to break on paragraph ("\n\n") or sentence-ending (".\n", ". ")
        boundaries near the target chunk_size to produce more semantically
        coherent chunks.

        Returns list of (start_offset, chunk_text).
        """
        if len(text) <= chunk_size:
            return [(0, text)]

        windows: list[tuple[int, str]] = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end >= len(text):
                # Last chunk — take everything remaining
                windows.append((start, text[start:]))
                break

            # Try to find a good break point near `end`
            best_break = cls._find_break_point(text, end, chunk_size)
            windows.append((start, text[start:best_break]))

            # Next window starts overlap characters before the break
            start = best_break - overlap
            if start < 0:
                start = 0
            # Avoid infinite loop
            if start >= best_break:
                start = best_break

        return windows

    @staticmethod
    def _find_break_point(text: str, target: int, chunk_size: int) -> int:
        """
        Find a natural break point near `target` offset.
        Searches backwards from target for paragraph or sentence boundaries.
        """
        search_start = max(target - chunk_size // 4, 0)
        search_region = text[search_start:target]

        # Prefer paragraph break
        para_idx = search_region.rfind("\n\n")
        if para_idx != -1 and para_idx > len(search_region) // 2:
            return search_start + para_idx + 2

        # Prefer sentence end
        for sep in (". ", ".\n", "? ", "! "):
            sent_idx = search_region.rfind(sep)
            if sent_idx != -1 and sent_idx > len(search_region) // 2:
                return search_start + sent_idx + len(sep)

        # Fall back to target
        return target

    @staticmethod
    def _page_for_offset(
        offset_to_page: list[tuple[int, int]], offset: int
    ) -> int:
        """Binary-search-style lookup: which page does `offset` belong to?"""
        result_page = offset_to_page[0][1] if offset_to_page else 1
        for seg_offset, page_num in offset_to_page:
            if seg_offset <= offset:
                result_page = page_num
            else:
                break
        return result_page
