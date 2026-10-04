import asyncio
import sys
import shutil
from pathlib import Path
import json

from app.services.document_store import DocumentStore
from app.services.vector_store import VectorStore
from app.services.pdf_service import PDFService
from app.services.chapter_service import ChapterService
from app.services.chunking_service import ChunkingService, ChunkConfig
from app.services.embedding_service import EmbeddingService
from app.models.document import DocumentMeta, ProcessingStatus
from app.core.config import settings

async def reprocess_all():
    print("Clearing ChromaDB and Document Store...")
    # Clear ChromaDB completely
    VectorStore._client = None
    if settings.CHROMA_DIR.exists():
        # Due to lock files, sometimes shutil.rmtree fails on Windows.
        # We'll just delete the document from vector store instead.
        pass

    # Read current docs
    docs = DocumentStore.list_all()
    if not docs:
        print("No documents to reprocess.")
        return

    for doc in docs:
        print(f"\nReprocessing {doc.document_id} ({doc.document_name})")
        
        # 1. Delete from Vector Store
        try:
            VectorStore.delete_document(doc.document_id)
            print(f"  - Deleted old vectors from ChromaDB")
        except Exception as e:
            print(f"  - Warning: Failed to delete old vectors: {e}")

        # 2. Reset status
        doc.processing_status = ProcessingStatus.PROCESSING
        doc.chapters = []
        doc.error_message = None
        DocumentStore.save(doc)

        file_path = settings.UPLOADS_DIR / f"{doc.document_id}_{doc.document_name}"
        if not file_path.exists():
            print(f"  - Error: PDF not found at {file_path}")
            continue

        try:
            print("  - Extracting pages...")
            pages = PDFService.extract_pages(file_path)
            toc = PDFService.extract_toc(file_path)
            
            print("  - Detecting chapters...")
            chapters = ChapterService.detect_chapters(pages, toc)
            doc.chapters = chapters
            for ch in chapters:
                print(f"      Chapter {ch.chapter_number}: {ch.chapter_title}")

            print("  - Chunking document...")
            config = ChunkConfig()
            chunks = ChunkingService.chunk_document(
                pages=pages,
                chapters=chapters,
                document_id=doc.document_id,
                document_name=doc.document_name,
                class_name=doc.class_name,
                subject=doc.subject,
                config=config
            )
            print(f"      Created {len(chunks)} chunks")

            print("  - Generating embeddings...")
            embeddings = EmbeddingService.embed_texts([c.text for c in chunks])

            print("  - Ingesting to ChromaDB...")
            VectorStore.ingest_chunks(doc.document_id, chunks, embeddings)

            doc.processing_status = ProcessingStatus.PROCESSED
            DocumentStore.save(doc)
            print(f"  - Successfully reprocessed {doc.document_name}")
            
        except Exception as e:
            doc.processing_status = ProcessingStatus.FAILED
            doc.error_message = str(e)
            DocumentStore.save(doc)
            print(f"  - Failed to process: {e}")

if __name__ == "__main__":
    asyncio.run(reprocess_all())
