import os
import uuid
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import (
    DocumentUploadResponse,
    DocumentMetadata,
    DocumentListResponse,
    DeleteDocumentResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ClearHistoryResponse,
    SettingsUpdateRequest
)
from app.core.document_loader import DocumentLoader, DocumentExtractionError
from app.core.text_splitter import DocumentChunker
from app.core.vector_store import vector_store_manager
from app.core.rag_chain import rag_pipeline
from app.core.llm_provider import llm_provider, LLMProviderError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_directories()
    logger.info("DocuIntel AI RAG Backend initialized successfully.")
    yield

# FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for local development and multi-origin flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and Template mounts
STATIC_DIR = settings.BASE_DIR / "app" / "static"
TEMPLATES_DIR = settings.BASE_DIR / "app" / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory Conversation History Store (keyed by session_id)
# Each entry is a list of {"role": "user"|"assistant", "content": str, "timestamp": str, "sources": list}
conversation_sessions: Dict[str, List[Dict[str, Any]]] = {}

# UI Route
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Renders the main 3-panel dashboard."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "active_provider": llm_provider.provider,
        "active_model": llm_provider.gemini_model if llm_provider.provider == "gemini" else llm_provider.openai_model,
        "api_key_configured": settings.is_api_key_configured()
    })

# ==============================================================================
# DOCUMENT MANAGEMENT ENDPOINTS
# ==============================================================================

@app.post("/upload", response_model=DocumentUploadResponse)
@app.post("/api/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a document (PDF, DOCX, TXT), validates it, checks for duplicates,
    extracts text, chunks it, generates embeddings, and indexes it into ChromaDB.
    """
    filename = file.filename or "uploaded_file"
    file_ext = Path(filename).suffix.lower()

    # 1. Validate file extension
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{file_ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 2. Check for duplicate upload
    existing_id = vector_store_manager.is_duplicate(filename)
    if existing_id:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": f"Document '{filename}' is already indexed in the knowledge base (Doc ID: {existing_id}). Please remove it first to re-index."
            }
        )

    # 3. Read content & validate file size
    contents = await file.read()
    file_size = len(contents)
    
    is_valid, err_msg = DocumentLoader.validate_file(filename, file_size)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)

    # 4. Save to temporary/persistent upload folder
    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    safe_filename = f"{doc_id}_{filename}"
    saved_path = settings.UPLOAD_DIR / safe_filename

    try:
        with open(saved_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error(f"Failed to save upload file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file on server: {str(e)}")

    # 5. Extract text from document
    try:
        pages = DocumentLoader.load_document(saved_path)
    except DocumentExtractionError as e:
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(status_code=500, detail=f"Extraction failure: {str(e)}")

    # 6. Chunk text
    chunker = DocumentChunker()
    chunks = chunker.chunk_document_pages(doc_id=doc_id, pages=pages)

    if not chunks:
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(
            status_code=422, 
            detail=f"No meaningful text chunks could be extracted from '{filename}'."
        )

    # 7. Index in ChromaDB & metadata registry
    doc_metadata = {
        "doc_id": doc_id,
        "filename": filename,
        "stored_filename": safe_filename,
        "file_path": str(saved_path),
        "file_type": file_ext,
        "file_size_bytes": file_size,
        "file_size_formatted": DocumentLoader.format_file_size(file_size),
        "page_count": len(pages),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        vector_store_manager.add_document(doc_metadata=doc_metadata, chunks=chunks)
    except Exception as e:
        logger.error(f"Vector store indexing failed: {e}")
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings and index document: {str(e)}")

    metadata_response = DocumentMetadata(
        doc_id=doc_id,
        filename=filename,
        file_type=file_ext,
        file_size_bytes=file_size,
        file_size_formatted=DocumentLoader.format_file_size(file_size),
        chunk_count=len(chunks),
        page_count=len(pages),
        uploaded_at=doc_metadata["uploaded_at"]
    )

    return DocumentUploadResponse(
        success=True,
        message=f"Successfully indexed '{filename}' into {len(chunks)} chunks across {len(pages)} page(s).",
        document=metadata_response
    )

@app.get("/documents", response_model=DocumentListResponse)
@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents():
    """Lists all currently indexed documents with chunk and page counts."""
    docs = vector_store_manager.list_documents()
    formatted = []
    total_chunks = 0

    for d in docs:
        c_count = d.get("chunk_count", 0)
        total_chunks += c_count
        formatted.append(DocumentMetadata(
            doc_id=d["doc_id"],
            filename=d.get("filename", "unknown"),
            file_type=d.get("file_type", ""),
            file_size_bytes=d.get("file_size_bytes", 0),
            file_size_formatted=d.get("file_size_formatted", "0 B"),
            chunk_count=c_count,
            page_count=d.get("page_count", 1),
            uploaded_at=d.get("uploaded_at", "")
        ))

    return DocumentListResponse(
        documents=formatted,
        total_documents=len(formatted),
        total_chunks=total_chunks
    )

@app.delete("/documents/{doc_id}", response_model=DeleteDocumentResponse)
@app.delete("/api/documents/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(doc_id: str):
    """Deletes a document from the vector store, filesystem, and registry."""
    success = vector_store_manager.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found.")

    return DeleteDocumentResponse(
        success=True,
        message=f"Document '{doc_id}' removed from knowledge base.",
        doc_id=doc_id
    )

# ==============================================================================
# CHAT & RAG QUERY ENDPOINTS
# ==============================================================================

@app.post("/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """
    RAG conversational query endpoint:
    Retrieves relevant document context, grounds LLM answer, and returns structured sources.
    """
    session_id = request.session_id or "default"
    user_query = request.message.strip()

    if not user_query:
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")

    # Retrieve prior session history
    session_history = conversation_sessions.get(session_id, [])

    # Format history for LLM provider (last 6 turns for conversational context)
    formatted_history = []
    for turn in session_history[-6:]:
        formatted_history.append({
            "role": turn.get("role", "user"),
            "content": turn.get("content", "")
        })

    # Execute RAG Pipeline
    try:
        rag_result = rag_pipeline.query(
            question=user_query,
            conversation_history=formatted_history,
            top_k=request.top_k
        )
    except LLMProviderError as e:
        logger.error(f"LLM Provider Error in /chat: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    except Exception as e:
        logger.exception("Unexpected error in RAG query")
        raise HTTPException(status_code=500, detail=f"Internal RAG pipeline error: {str(e)}")

    answer_text = rag_result["answer"]
    sources = rag_result["sources"]

    # Append to conversation session history
    timestamp_str = datetime.now().strftime("%I:%M %p")
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = []

    conversation_sessions[session_id].append({
        "role": "user",
        "content": user_query,
        "timestamp": timestamp_str
    })

    conversation_sessions[session_id].append({
        "role": "assistant",
        "content": answer_text,
        "timestamp": timestamp_str,
        "sources": [s.dict() for s in sources]
    })

    return ChatResponse(
        answer=answer_text,
        sources=sources,
        session_id=session_id,
        retrieved_chunks_count=rag_result["retrieved_chunks_count"],
        latency_ms=rag_result["latency_ms"],
        model_used=rag_result["model_used"],
        provider_used=rag_result["provider_used"]
    )

@app.get("/history")
@app.get("/api/history")
async def get_history(session_id: str = "default"):
    """Fetches conversation history for a given session."""
    history = conversation_sessions.get(session_id, [])
    return {
        "session_id": session_id,
        "total_messages": len(history),
        "messages": history
    }

@app.delete("/history")
@app.delete("/api/history")
async def clear_history(session_id: str = "default"):
    """Clears conversational history for the given session."""
    if session_id in conversation_sessions:
        conversation_sessions[session_id] = []
    return ClearHistoryResponse(
        success=True,
        message=f"Conversation history for session '{session_id}' cleared.",
        session_id=session_id
    )

# ==============================================================================
# SYSTEM & HEALTH ENDPOINTS
# ==============================================================================

@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Returns application health, provider credentials status, and vector DB stats."""
    stats = vector_store_manager.get_stats()
    provider_info = llm_provider.get_active_provider_info()

    return HealthResponse(
        status="healthy",
        provider=provider_info["provider"],
        model=provider_info["model"],
        api_key_configured=provider_info["api_key_configured"],
        embedding_provider=stats["embedding_provider"],
        embedding_model=stats["embedding_model"],
        total_documents=stats["total_documents"],
        total_chunks=stats["total_chunks"],
        storage_path=stats["storage_path"]
    )

@app.get("/stats")
@app.get("/api/stats")
async def get_stats():
    """Returns vector database and document statistics."""
    return vector_store_manager.get_stats()

@app.post("/settings")
@app.post("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Allows updating LLM provider, API key, and model at runtime."""
    llm_provider.update_credentials(
        provider=req.provider,
        api_key=req.api_key,
        model=req.model
    )
    provider_info = llm_provider.get_active_provider_info()
    return {
        "success": True,
        "message": "Settings updated successfully.",
        **provider_info
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
