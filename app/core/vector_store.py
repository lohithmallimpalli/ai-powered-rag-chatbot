import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    Manages persistent ChromaDB vector storage, embedding generation,
    document indexing, metadata querying, and similarity search.
    """

    COLLECTION_NAME = "document_intelligence_rag"
    DOC_REGISTRY_FILE = "documents_registry.json"

    def __init__(self):
        settings.ensure_directories()
        self.chroma_dir = settings.CHROMA_DIR
        self.registry_path = self.chroma_dir / self.DOC_REGISTRY_FILE
        self._init_embedding_function()
        self._init_client()

    def _init_embedding_function(self):
        """Initializes the embedding model based on settings."""
        try:
            from chromadb.utils import embedding_functions
            # SentenceTransformers embedding function
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL_NAME
            )
            logger.info(f"Initialized embedding model: {settings.EMBEDDING_MODEL_NAME}")
        except Exception as e:
            logger.warning(f"Failed to load SentenceTransformerEmbeddingFunction ({e}). Falling back to DefaultEmbeddingFunction.")
            from chromadb.utils import embedding_functions
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    def _init_client(self):
        """Initializes persistent Chroma client and collection."""
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        self._ensure_registry()

    def _ensure_registry(self):
        if not self.registry_path.exists():
            self._save_registry({})

    def _load_registry(self) -> Dict[str, Any]:
        try:
            if self.registry_path.exists():
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading document registry: {e}")
        return {}

    def _save_registry(self, data: Dict[str, Any]):
        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving document registry: {e}")

    def is_duplicate(self, filename: str) -> Optional[str]:
        """Checks if a document with the exact filename already exists in registry."""
        registry = self._load_registry()
        for doc_id, doc_info in registry.items():
            if doc_info.get("filename") == filename:
                return doc_id
        return None

    def add_document(self, doc_metadata: Dict[str, Any], chunks: List[Dict[str, Any]]) -> bool:
        """
        Embeds and indexes document chunks in ChromaDB, updating the metadata registry.
        """
        if not chunks:
            return False

        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]

        # ChromaDB add
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        # Update registry
        registry = self._load_registry()
        doc_id = doc_metadata["doc_id"]
        registry[doc_id] = {
            **doc_metadata,
            "chunk_count": len(chunks)
        }
        self._save_registry(registry)
        logger.info(f"Successfully indexed document {doc_id} with {len(chunks)} chunks.")
        return True

    def delete_document(self, doc_id: str) -> bool:
        """Deletes all chunks and metadata associated with a document ID."""
        registry = self._load_registry()
        if doc_id not in registry:
            return False

        try:
            # Delete from ChromaDB by metadata filter
            self.collection.delete(where={"doc_id": doc_id})
        except Exception as e:
            logger.warning(f"Chroma delete for doc_id={doc_id} returned: {e}")

        # Also remove physical file if stored
        file_path_str = registry[doc_id].get("file_path")
        if file_path_str and Path(file_path_str).exists():
            try:
                Path(file_path_str).unlink()
            except Exception as e:
                logger.error(f"Error removing file {file_path_str}: {e}")

        # Remove from registry
        del registry[doc_id]
        self._save_registry(registry)
        logger.info(f"Deleted document {doc_id} from vector store and registry.")
        return True

    def similarity_search(
        self, 
        query: str, 
        top_k: int = None, 
        score_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic similarity search against indexed document chunks.
        Returns sorted list of matching chunk dictionaries with cosine similarity score.
        """
        k = top_k or settings.TOP_K_RETRIEVAL
        total_chunks = self.collection.count()
        if total_chunks == 0:
            return []

        k = min(k, total_chunks)

        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        retrieved_chunks = []
        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results.get("distances", [[]])[0]

        for i in range(len(docs)):
            dist = distances[i] if i < len(distances) else 1.0
            # For cosine distance, similarity = 1 - distance
            # Chroma returns cosine distance in [0, 2]
            similarity = max(0.0, 1.0 - dist)
            
            threshold = score_threshold if score_threshold is not None else settings.SIMILARITY_THRESHOLD
            if similarity < threshold:
                continue

            meta = metadatas[i] or {}
            retrieved_chunks.append({
                "chunk_id": results["ids"][0][i] if results.get("ids") else f"chunk_{i}",
                "text": docs[i],
                "score": round(similarity, 4),
                "document_id": meta.get("doc_id", "unknown"),
                "filename": meta.get("filename", "Unknown Document"),
                "page": meta.get("page", 1),
                "chunk_index": meta.get("chunk_index", 0),
                "file_type": meta.get("file_type", "")
            })

        return retrieved_chunks

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns all registered documents."""
        registry = self._load_registry()
        return list(registry.values())

    def get_stats(self) -> Dict[str, Any]:
        """Returns stats about indexed knowledge base."""
        registry = self._load_registry()
        total_docs = len(registry)
        total_chunks = self.collection.count()
        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_model": settings.EMBEDDING_MODEL_NAME,
            "storage_path": str(self.chroma_dir)
        }

# Global singleton
vector_store_manager = VectorStoreManager()
