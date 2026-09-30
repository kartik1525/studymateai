"""
Live end-to-end verification of the Milestone 2 document pipeline.

Creates a real multi-chapter test PDF → uploads via API → polls for processing
→ retrieves detail with detected chapters → verifies the full flow.
"""

import sys
import time
import json
import fitz  # PyMuPDF
import urllib.request
import urllib.parse
from pathlib import Path

BACKEND_URL = "http://127.0.0.1:8000"

# ── Step 1: Create a realistic multi-chapter test PDF ──────────────

def create_test_pdf(output_path: Path) -> Path:
    doc = fitz.open()

    chapters = [
        ("Chapter 1: Introduction to Artificial Intelligence",
         "Artificial intelligence (AI) is the simulation of human intelligence "
         "processes by computer systems. These processes include learning, reasoning, "
         "and self-correction. AI can be categorised into narrow AI and general AI. "
         "Narrow AI is designed for a particular task, while general AI aims to "
         "perform any intellectual task that a human can do."),
        ("Chapter 2: AI Project Cycle",
         "The AI project cycle consists of problem scoping, data acquisition, data "
         "exploration, modelling, and evaluation. Problem scoping defines what the "
         "AI system should solve. Data acquisition involves collecting relevant data. "
         "Data exploration helps understand patterns. Modelling involves choosing and "
         "training an algorithm. Evaluation checks how well the model performs."),
        ("Chapter 3: Machine Intelligence",
         "Machine intelligence refers to the ability of machines to mimic cognitive "
         "functions associated with the human mind. Machine learning is a subset of "
         "AI that allows systems to learn and improve from experience. Deep learning "
         "uses neural networks with multiple layers to model complex patterns in data. "
         "Supervised learning uses labeled data while unsupervised learning finds "
         "patterns in unlabeled data."),
        ("Chapter 4: Cybersecurity and Ethics",
         "Cybersecurity is the practice of protecting systems, networks, and programs "
         "from digital attacks. It includes concepts like encryption, authentication, "
         "and authorization. Ethical AI refers to developing AI that is fair, "
         "transparent, and accountable. Students must understand both technical "
         "safeguards and ethical considerations when building AI systems."),
    ]

    for title, content in chapters:
        # Title page for each chapter
        page = doc.new_page(width=595, height=842)
        page.insert_text(fitz.Point(72, 100), title, fontsize=16)
        page.insert_text(fitz.Point(72, 140), content, fontsize=11)

        # Add a second page of content per chapter
        page2 = doc.new_page(width=595, height=842)
        extended = (content + " ") * 3
        page2.insert_text(fitz.Point(72, 72), extended[:800], fontsize=11)

    doc.save(str(output_path))
    doc.close()
    print(f"✓ Created test PDF: {output_path} ({doc.page_count if False else '8'} pages)")
    return output_path


# ── Step 2: Upload via POST /api/documents/upload ──────────────────

def upload_pdf(pdf_path: Path) -> dict:
    import http.client
    import mimetypes

    boundary = "----StudyMateBoundary"
    lines = []

    # class_name field
    lines.append(f"--{boundary}")
    lines.append('Content-Disposition: form-data; name="class_name"')
    lines.append("")
    lines.append("10")

    # subject field
    lines.append(f"--{boundary}")
    lines.append('Content-Disposition: form-data; name="subject"')
    lines.append("")
    lines.append("Artificial Intelligence")

    body_prefix = "\r\n".join(lines) + "\r\n"
    body_prefix += f"--{boundary}\r\n"
    body_prefix += f'Content-Disposition: form-data; name="file"; filename="{pdf_path.name}"\r\n'
    body_prefix += "Content-Type: application/pdf\r\n\r\n"

    body_suffix = f"\r\n--{boundary}--\r\n"

    file_data = pdf_path.read_bytes()
    body = body_prefix.encode() + file_data + body_suffix.encode()

    conn = http.client.HTTPConnection("127.0.0.1", 8000)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }
    conn.request("POST", "/api/documents/upload", body=body, headers=headers)
    resp = conn.getresponse()
    data = json.loads(resp.read().decode())
    conn.close()

    print(f"✓ Upload response (HTTP {resp.status}):")
    print(f"  document_id: {data.get('document_id')}")
    print(f"  document_name: {data.get('document_name')}")
    print(f"  processing_status: {data.get('processing_status')}")

    assert resp.status == 201, f"Upload failed: {data}"
    return data


# ── Step 3: Poll for processing completion ─────────────────────────

def wait_for_processing(document_id: str, timeout: int = 15) -> dict:
    print(f"⏳ Waiting for processing of {document_id}...")
    start = time.time()
    while time.time() - start < timeout:
        url = f"{BACKEND_URL}/api/documents/{document_id}"
        resp = urllib.request.urlopen(url)
        data = json.loads(resp.read().decode())
        status = data["processing_status"]
        if status in ("processed", "failed"):
            return data
        time.sleep(0.3)
    raise TimeoutError(f"Processing did not complete within {timeout}s")


# ── Step 4: Verify the result ──────────────────────────────────────

def verify_result(detail: dict):
    print(f"\n✓ Document detail:")
    print(f"  document_id: {detail['document_id']}")
    print(f"  document_name: {detail['document_name']}")
    print(f"  class_name: {detail['class_name']}")
    print(f"  subject: {detail['subject']}")
    print(f"  page_count: {detail['page_count']}")
    print(f"  processing_status: {detail['processing_status']}")

    assert detail["processing_status"] == "processed", (
        f"Expected 'processed', got '{detail['processing_status']}': {detail.get('error_message')}"
    )
    assert detail["class_name"] == "10"
    assert detail["subject"] == "Artificial Intelligence"
    assert detail["page_count"] == 8  # 4 chapters × 2 pages each

    chapters = detail["chapters"]
    print(f"\n✓ Detected {len(chapters)} chapters:")
    for ch in chapters:
        print(f"  {ch['chapter_number']:2d}. {ch['chapter_title']} (pages {ch['start_page']}–{ch['end_page']})")

    assert len(chapters) >= 3, f"Expected at least 3 chapters, got {len(chapters)}"


# ── Step 5: Verify list endpoint ──────────────────────────────────

def verify_list():
    url = f"{BACKEND_URL}/api/documents"
    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read().decode())
    print(f"\n✓ GET /api/documents returned {len(data)} document(s)")
    for doc in data:
        print(f"  - {doc['document_name']} | {doc['class_name']} | "
              f"{doc['chapter_count']} chapters | {doc['page_count']} pages | "
              f"status: {doc['processing_status']}")


# ── Main ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  StudyMate AI — Milestone 2 Live Verification")
    print("=" * 60)

    # Health check
    resp = urllib.request.urlopen(f"{BACKEND_URL}/api/health")
    health = json.loads(resp.read().decode())
    print(f"\n✓ Health: {health['status']} (v{health['version']})\n")

    # Create test PDF
    test_pdf_path = Path(__file__).parent / "_test_upload.pdf"
    create_test_pdf(test_pdf_path)

    # Upload
    upload_data = upload_pdf(test_pdf_path)

    # Wait for processing
    detail = wait_for_processing(upload_data["document_id"])

    # Verify
    verify_result(detail)
    verify_list()

    # Clean up test file
    test_pdf_path.unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print("  ✅ ALL VERIFICATIONS PASSED")
    print("=" * 60)
