"""
Internal demonstration script for the RAG pipeline.

Shows the full flow:
1. Create a test PDF
2. Extract text and detect chapters
3. Chunk into semantic segments
4. Embed via Gemini and store in ChromaDB
5. Query with chapter restrictions
6. Verify output
"""

import sys
import logging
from pathlib import Path

# Setup simple logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

from app.services.pdf_service import PDFService
from app.services.chapter_service import ChapterService
from app.services.chunking_service import ChunkingService, ChunkConfig
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.retrieval_service import RetrievalService
from tests.test_documents import create_text_pdf

def run_demo():
    print("=" * 60)
    print("  StudyMate AI — RAG Pipeline Demonstration")
    print("=" * 60)

    # 1. Create a test PDF
    pdf_path = Path(__file__).parent / "_rag_demo.pdf"
    
    pages = [
        "Chapter 1: Biology Basics\nCells are the basic unit of life. " * 15,
        "More about cells and their functions. " * 15,
        "Chapter 2: Physics Basics\nNewton's laws of motion describe how objects move. " * 15,
        "More about forces and gravity. " * 15,
        "Chapter 3: Chemistry Basics\nAtoms and molecules form the basis of all matter. " * 15,
    ]
    
    print("\n[1] Creating test PDF...")
    create_text_pdf(pdf_path, pages)
    
    document_id = "doc_ragdemo123"
    
    try:
        # 2. Extract and detect chapters
        print("\n[2] Extracting text and detecting chapters...")
        extracted_pages = PDFService.extract_pages(pdf_path)
        toc = PDFService.extract_toc(pdf_path)
        chapters = ChapterService.detect_chapters(extracted_pages, toc=toc)
        
        for ch in chapters:
            print(f"    Detected: {ch.chapter_title} (Pages {ch.start_page}-{ch.end_page})")

        # 3. Semantic chunking
        print("\n[3] Chunking document text...")
        config = ChunkConfig(chunk_size=300, chunk_overlap=50)
        chunks = ChunkingService.chunk_document(
            pages=extracted_pages,
            chapters=chapters,
            document_id=document_id,
            document_name="Science_Textbook.pdf",
            class_name="10",
            subject="Science",
            config=config
        )
        print(f"    Created {len(chunks)} chunks.")

        # 4. Embed and Ingest
        print("\n[4] Generating embeddings and storing in ChromaDB...")
        chunk_texts = [c.text for c in chunks]
        
        try:
            embeddings = EmbeddingService.embed_texts(chunk_texts)
        except Exception as e:
            print(f"\n❌ Error calling Gemini API: {e}")
            print("Please ensure GEMINI_API_KEY is correctly set in backend/.env")
            return
            
        ingested = VectorStore.ingest_chunks(document_id, chunks, embeddings)
        print(f"    Ingested {ingested} vectors into ChromaDB.")

        # 5. Querying (Testing the critical requirement)
        print("\n[5] Testing retrieval (Chapter filtering)...")
        
        query = "Tell me about Newton's laws and forces."
        
        print(f"\n  Query: '{query}'")
        print(f"  Constraint: ONLY search in Chapter 2 (Physics)")
        
        results_ch2 = RetrievalService.retrieve(
            document_id=document_id,
            selected_chapters=[2],
            query=query,
            top_k=3
        )
        
        for i, res in enumerate(results_ch2, 1):
            print(f"    Result {i} (Score: {res.relevance_score:.2f}, Ch: {res.chapter_number} - {res.chapter_title})")
            # print(f"    Text snippet: {res.text[:80]}...")
            assert res.chapter_number == 2, "CRITICAL FAILURE: Leaked result from outside chapter 2!"
            
        print(f"\n  Query: '{query}'")
        print(f"  Constraint: ONLY search in Chapter 1 (Biology)")
        
        results_ch1 = RetrievalService.retrieve(
            document_id=document_id,
            selected_chapters=[1],
            query=query,
            top_k=3
        )
        
        for i, res in enumerate(results_ch1, 1):
            print(f"    Result {i} (Score: {res.relevance_score:.2f}, Ch: {res.chapter_number} - {res.chapter_title})")
            assert res.chapter_number == 1, "CRITICAL FAILURE: Leaked result from outside chapter 1!"

        print("\n" + "=" * 60)
        print("  ✅ DEMONSTRATION SUCCESSFUL")
        print("  Chapter isolation is working perfectly.")
        print("=" * 60)
        
    finally:
        # Cleanup
        if pdf_path.exists():
            pdf_path.unlink()
        # Clean up ChromaDB collection
        VectorStore.delete_document(document_id)

if __name__ == "__main__":
    run_demo()
