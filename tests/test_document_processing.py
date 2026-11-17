import pytest
from pathlib import Path
from app.core.document_loader import DocumentLoader, DocumentExtractionError
from app.core.text_splitter import DocumentChunker

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_documents"

def test_file_validator():
    # Valid file
    valid, msg = DocumentLoader.validate_file("test.pdf", 1024)
    assert valid is True
    assert msg == ""

    # Invalid extension
    valid, msg = DocumentLoader.validate_file("malicious.exe", 1024)
    assert valid is False
    assert "Unsupported file type" in msg

    # Oversize file (>25MB)
    valid, msg = DocumentLoader.validate_file("huge.pdf", 30 * 1024 * 1024)
    assert valid is False
    assert "exceeds maximum limit" in msg

    # Empty file
    valid, msg = DocumentLoader.validate_file("empty.txt", 0)
    assert valid is False
    assert "empty" in msg

def test_txt_extraction():
    txt_path = SAMPLE_DIR / "Global_AI_Security_Policy.txt"
    assert txt_path.exists()

    pages = DocumentLoader.load_document(txt_path)
    assert len(pages) == 1
    assert pages[0]["file_type"] == ".txt"
    assert "ARTIFICIAL INTELLIGENCE & DATA SECURITY POLICY" in pages[0]["text"]
    assert pages[0]["page"] == 1

def test_docx_extraction():
    docx_path = SAMPLE_DIR / "Q3_Financial_Performance_Report.docx"
    assert docx_path.exists()

    pages = DocumentLoader.load_document(docx_path)
    assert len(pages) == 1
    assert pages[0]["file_type"] == ".docx"
    assert "Apex Global Enterprises" in pages[0]["text"]
    assert "142.8 million" in pages[0]["text"]
    # Verify table data was extracted
    assert "Enterprise Software" in pages[0]["text"]

def test_pdf_extraction_and_pages():
    pdf_path = SAMPLE_DIR / "Cloud_Architecture_and_SLA.pdf"
    assert pdf_path.exists()

    pages = DocumentLoader.load_document(pdf_path)
    assert len(pages) == 3  # Our test PDF has 3 pages
    
    # Check page 1
    assert pages[0]["page"] == 1
    assert "Enterprise Cloud Architecture" in pages[0]["text"]
    
    # Check page 2
    assert pages[1]["page"] == 2
    assert "Severity 1" in pages[1]["text"]
    
    # Check page 3
    assert pages[2]["page"] == 3
    assert "Disaster Recovery" in pages[2]["text"]

def test_text_chunking_with_metadata():
    pdf_path = SAMPLE_DIR / "Cloud_Architecture_and_SLA.pdf"
    pages = DocumentLoader.load_document(pdf_path)
    
    chunker = DocumentChunker(chunk_size=400, chunk_overlap=50)
    chunks = chunker.chunk_document_pages(doc_id="doc_test_123", pages=pages)

    assert len(chunks) > 0
    first_chunk = chunks[0]
    
    assert "chunk_id" in first_chunk
    assert first_chunk["doc_id"] == "doc_test_123"
    assert "metadata" in first_chunk
    assert first_chunk["metadata"]["doc_id"] == "doc_test_123"
    assert first_chunk["metadata"]["filename"] == "Cloud_Architecture_and_SLA.pdf"
    assert first_chunk["metadata"]["page"] in [1, 2, 3]
    assert isinstance(first_chunk["metadata"]["chunk_index"], int)
