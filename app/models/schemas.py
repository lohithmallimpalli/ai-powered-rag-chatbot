from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class SourceReference(BaseModel):
    document_id: str = Field(..., description="ID of source document")
    filename: str = Field(..., description="Name of source file")
    page: Optional[int] = Field(None, description="Page number if PDF, or None")
    chunk_index: int = Field(0, description="Index of the chunk in document")
    score: Optional[float] = Field(None, description="Cosine similarity score")
    snippet: str = Field(..., description="Excerpt of the retrieved context")

class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    file_size_formatted: str
    chunk_count: int
    page_count: Optional[int] = 1
    uploaded_at: str

class DocumentUploadResponse(BaseModel):
    success: bool
    message: str
    document: Optional[DocumentMetadata] = None

class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata]
    total_documents: int
    total_chunks: int

class DeleteDocumentResponse(BaseModel):
    success: bool
    message: str
    doc_id: str

class ChatMessageItem(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    timestamp: Optional[str] = None
    sources: Optional[List[SourceReference]] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question or prompt")
    session_id: Optional[str] = Field("default", description="Conversation session ID")
    conversation_history: Optional[List[ChatMessageItem]] = Field(default_factory=list)
    top_k: Optional[int] = Field(None, description="Optional override for chunk retrieval count")

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceReference] = Field(default_factory=list)
    session_id: str
    retrieved_chunks_count: int
    latency_ms: float
    model_used: str
    provider_used: str

class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str
    api_key_configured: bool
    embedding_provider: str
    embedding_model: str
    total_documents: int
    total_chunks: int
    storage_path: str

class ClearHistoryResponse(BaseModel):
    success: bool
    message: str
    session_id: str

class SettingsUpdateRequest(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
