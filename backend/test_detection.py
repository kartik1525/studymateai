import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from app.services.pdf_service import PDFService
from app.services.chapter_service import ChapterService
from pathlib import Path

uploads = Path('data/uploads')
for f in uploads.glob('*.pdf'):
    if 'science' in f.name.lower() or 'Science' in f.name:
        print(f'File: {f.name}')
        pages = PDFService.extract_pages(f)
        toc = PDFService.extract_toc(f)
        print(f'TOC: {toc}')
        chapters = ChapterService.detect_chapters(pages, toc)
        for ch in chapters:
            print(f'  Chapter {ch.chapter_number}: "{ch.chapter_title}" (pages {ch.start_page}-{ch.end_page})')
