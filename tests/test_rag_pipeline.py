import pytest
from pathlib import Path
from app.core.document_loader import DocumentLoader
from app.core.text_splitter import DocumentChunker
from app.core.vector_store import VectorStoreManager
from app.core.rag_chain import RAGPipeline

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_documents"

@pytest.fixture
def vector_mgr(tmp_path):
    """Creates an isolated VectorStoreManager using temporary directory."""
    import chromadb
    from app.config import settings
    
    test_chroma_dir = tmp_path / "test_chroma"
    test_chroma_dir.mkdir(parents=True, exist_ok=True)
    
    # Instantiate custom manager pointing to temp directory
    mgr = VectorStoreManager()
    mgr.chroma_dir = test_chroma_dir
    mgr.registry_path = test_chroma_dir / "test_registry.json"
    mgr.client = chromadb.PersistentClient(path=str(test_chroma_dir))
    mgr.collection = mgr.client.get_or_create_collection(
        name="test_rag_collection",
        embedding_function=mgr.embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    mgr._ensure_registry()
    return mgr

def test_vector_store_indexing_and_search(vector_mgr):
    # Load and chunk sample TXT document
    txt_path = SAMPLE_DIR / "Global_AI_Security_Policy.txt"
    pages = DocumentLoader.load_document(txt_path)
    chunker = DocumentChunker(chunk_size=300, chunk_overlap=50)
    chunks = chunker.chunk_document_pages(doc_id="doc_ai_policy_01", pages=pages)
    
    assert len(chunks) > 0

    doc_meta = {
        "doc_id": "doc_ai_policy_01",
        "filename": "Global_AI_Security_Policy.txt",
        "file_type": ".txt",
        "file_size_bytes": 1200,
        "file_size_formatted": "1.2 KB",
        "page_count": 1,
        "uploaded_at": "2024-01-15 10:00:00"
    }

    # Index document
    success = vector_mgr.add_document(doc_metadata=doc_meta, chunks=chunks)
    assert success is True

    # Test duplicate detection
    dup_id = vector_mgr.is_duplicate("Global_AI_Security_Policy.txt")
    assert dup_id == "doc_ai_policy_01"

    # Test stats
    stats = vector_mgr.get_stats()
    assert stats["total_documents"] == 1
    assert stats["total_chunks"] == len(chunks)

    # Test similarity search for password policy
    results = vector_mgr.similarity_search("What is the password length requirement and rotation policy?", top_k=2)
    assert len(results) > 0
    top_result = results[0]
    assert "password" in top_result["text"].lower() or "14 characters" in top_result["text"].lower()
    assert top_result["document_id"] == "doc_ai_policy_01"
    assert top_result["filename"] == "Global_AI_Security_Policy.txt"
    assert top_result["score"] > 0.3

    # Test delete document
    del_success = vector_mgr.delete_document("doc_ai_policy_01")
    assert del_success is True

    # Check stats after delete
    stats_after = vector_mgr.get_stats()
    assert stats_after["total_documents"] == 0

def test_rag_pipeline_empty_knowledge_base():
    pipeline = RAGPipeline()
    # Query when vector store is empty or for a clean session
    result = pipeline.query("What is the SLA uptime guarantee?")
    assert "answer" in result
    assert "sources" in result
    assert isinstance(result["sources"], list)
    assert "latency_ms" in result
