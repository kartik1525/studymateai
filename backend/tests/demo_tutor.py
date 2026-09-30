"""
Manual integration test for the Tutor API endpoint.

Shows the full flow:
1. Extract, Chunk, Embed, Ingest (RAG setup)
2. Call Tutor API for a single chapter
3. Verify sources
4. Verify insufficient context handling
"""

import sys
import logging
from pathlib import Path
from fastapi.testclient import TestClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

from app.main import app
from app.services.pdf_service import PDFService
from app.services.chapter_service import ChapterService
from app.services.chunking_service import ChunkingService, ChunkConfig
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.document_store import DocumentStore
from app.models.document import DocumentMeta, ProcessingStatus, Chapter
from tests.test_documents import create_text_pdf

client = TestClient(app)

def run_demo():
    print("=" * 60)
    print("  StudyMate AI — Tutor API Demonstration")
    print("=" * 60)

    # 1. Setup RAG context
    pdf_path = Path(__file__).parent / "_tutor_demo.pdf"
    
    pages = [
        "Chapter 1: The AI Project Cycle\nThe AI project cycle has 5 stages: Problem Scoping, Data Acquisition, Data Exploration, Modeling, and Evaluation.\n\n" * 10,
        "Chapter 2: Machine Intelligence\nMachine intelligence refers to computers performing cognitive tasks. Weak AI is narrow. Strong AI is general.\n\n" * 10,
        "Chapter 3: Ethics in AI\nAI systems must be fair, transparent, and unbiased. Bias in training data can lead to unfair predictions.\n\n" * 10,
    ]
    
    create_text_pdf(pdf_path, pages)
    
    document_id = "doc_tutordemo123"
    
    print("\n[1] Preparing document and RAG chunks...")
    try:
        pages = PDFService.extract_pages(pdf_path)
        toc = PDFService.extract_toc(pdf_path)
        chapters = ChapterService.detect_chapters(pages, toc=toc)
        
        # Save document metadata
        doc = DocumentMeta(
            document_id=document_id,
            document_name="TutorDemo.pdf",
            class_name="10",
            subject="AI",
            page_count=len(pages),
            chapters=chapters,
            processing_status=ProcessingStatus.PROCESSED
        )
        DocumentStore.save(doc)

        config = ChunkConfig(chunk_size=300, chunk_overlap=50)
        chunks = ChunkingService.chunk_document(
            pages=pages, chapters=chapters,
            document_id=document_id, document_name=doc.document_name,
            class_name=doc.class_name, subject=doc.subject, config=config
        )
        
        chunk_texts = [c.text for c in chunks]
        try:
            embeddings = EmbeddingService.embed_texts(chunk_texts)
        except Exception as e:
            print(f"\n❌ Error calling Gemini API: {e}")
            return
            
        VectorStore.ingest_chunks(document_id, chunks, embeddings)
        print("    Document ingested successfully.")

        # 2. Call Tutor API (Chapter 3)
        print("\n[2] Testing API (Selected Chapter: 3)...")
        response = client.post("/api/tutor/ask", json={
            "document_id": document_id,
            "chapters": [3],
            "question": "Why is bias in AI a problem?"
        })
        
        data = response.json()
        print(f"\n  Q: Why is bias in AI a problem?")
        print(f"  A: {data['answer']}")
        print(f"  Sources:")
        for src in data.get("sources", []):
            print(f"    - {src['chapter']} (Page {src['page']})")
            assert src['chapter'] == "Ethics in AI", "Leaked source!"

        # 3. Call Tutor API (Chapter 2 & 3)
        print("\n[3] Testing API (Selected Chapters: 2, 3)...")
        response = client.post("/api/tutor/ask", json={
            "document_id": document_id,
            "chapters": [2, 3],
            "question": "What is the difference between weak and strong AI?"
        })
        
        data = response.json()
        print(f"\n  Q: What is the difference between weak and strong AI?")
        print(f"  A: {data['answer']}")
        print(f"  Sources:")
        for src in data.get("sources", []):
            print(f"    - {src['chapter']} (Page {src['page']})")
            assert src['chapter'] == "Machine Intelligence", "Wrong source!"

        # 4. Test Insufficient Context
        print("\n[4] Testing API (Insufficient Context Fallback)...")
        print("    Asking a question about the AI Project Cycle (Chapter 1) but ONLY selecting Chapter 3.")
        
        response = client.post("/api/tutor/ask", json={
            "document_id": document_id,
            "chapters": [3],
            "question": "What are the 5 stages of the AI project cycle?"
        })
        
        data = response.json()
        print(f"\n  Q: What are the 5 stages of the AI project cycle?")
        print(f"  A: {data['answer']}")
        assert "couldn't find enough information" in data['answer'], "Fallback message failed!"
        
        print("\n" + "=" * 60)
        print("  ✅ TUTOR DEMONSTRATION SUCCESSFUL")
        print("=" * 60)
        
    finally:
        if pdf_path.exists():
            pdf_path.unlink()
        DocumentStore.delete(document_id)
        VectorStore.delete_document(document_id)

if __name__ == "__main__":
    run_demo()
