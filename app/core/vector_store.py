
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages ChromaDB with Gemini API embeddings."""

    # A separate collection prevents mixing old MiniLM vectors with Gemini vectors.
    COLLECTION_NAME = "document_intelligence_rag_gemini"
    DOC_REGISTRY_FILE = "documents_registry_gemini.json"
    EMBEDDING_MODEL = "gemini-embedding-001"
    EMBEDDING_DIMENSION = 768
    BATCH_SIZE = 20

    def __init__(self):
        settings.ensure_directories()

        self.chroma_dir = settings.CHROMA_DIR
        self.registry_path = self.chroma_dir / self.DOC_REGISTRY_FILE

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Configure it in your .env file "
                "or deployment environment variables."
            )

        self.genai_client = genai.Client(api_key=api_key)

        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        self._ensure_registry()
        logger.info("Gemini embedding vector store initialized.")

    def _embed_texts(self, texts: List[str], task_type: str) -> List[List[float]]:
        """Generate embeddings using the Gemini API."""
        if not texts:
            return []

        all_embeddings = []

        for start in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[start:start + self.BATCH_SIZE]

            response = self.genai_client.models.embed_content(
                model=self.EMBEDDING_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self.EMBEDDING_DIMENSION
                )
            )

            if not response.embeddings:
                raise RuntimeError("Gemini returned no embeddings.")

            batch_embeddings = [
                item.values for item in response.embeddings
            ]

            if len(batch_embeddings) != len(batch):
                raise RuntimeError("Gemini returned an unexpected number of embeddings.")

            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _ensure_registry(self):
        if not self.registry_path.exists():
            self._save_registry({})

    def _load_registry(self) -> Dict[str, Any]:
        try:
            if self.registry_path.exists():
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error("Error loading document registry: %s", e)

        return {}

    def _save_registry(self, data: Dict[str, Any]):
        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Error saving document registry: %s", e)
            raise

    def is_duplicate(self, filename: str) -> Optional[str]:
        registry = self._load_registry()

        for doc_id, doc_info in registry.items():
            if doc_info.get("filename") == filename:
                return doc_id

        return None

    def add_document(
        self,
        doc_metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ) -> bool:
        """Embed and index document chunks using Gemini."""
        if not chunks:
            return False

        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]

        embeddings = self._embed_texts(
            documents,
            task_type="RETRIEVAL_DOCUMENT"
        )

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

        registry = self._load_registry()
        doc_id = doc_metadata["doc_id"]

        registry[doc_id] = {
            **doc_metadata,
            "chunk_count": len(chunks)
        }

        self._save_registry(registry)

        logger.info(
            "Indexed document %s with %s chunks.",
            doc_id,
            len(chunks)
        )

        return True

    def delete_document(self, doc_id: str) -> bool:
        registry = self._load_registry()

        if doc_id not in registry:
            return False

        try:
            self.collection.delete(where={"doc_id": doc_id})
        except Exception as e:
            logger.warning("Chroma delete warning for %s: %s", doc_id, e)

        file_path_str = registry[doc_id].get("file_path")

        if file_path_str and Path(file_path_str).exists():
            try:
                Path(file_path_str).unlink()
            except Exception as e:
                logger.error("Error removing uploaded file: %s", e)

        del registry[doc_id]
        self._save_registry(registry)

        return True

    def similarity_search(
        self,
        query: str,
        top_k: int = None,
        score_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Search document chunks using Gemini query embeddings."""

        total_chunks = self.collection.count()

        if total_chunks == 0:
            return []

        k = top_k or settings.TOP_K_RETRIEVAL
        k = min(k, total_chunks)

        query_embedding = self._embed_texts(
            [query],
            task_type="RETRIEVAL_QUERY"
        )[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        retrieved_chunks = []

        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results.get("distances", [[]])[0]

        threshold = (
            score_threshold
            if score_threshold is not None
            else settings.SIMILARITY_THRESHOLD
        )

        for i, document in enumerate(docs):
            distance = distances[i] if i < len(distances) else 1.0
            similarity = max(0.0, 1.0 - distance)

            if similarity < threshold:
                continue

            metadata = metadatas[i] or {}

            retrieved_chunks.append({
                "chunk_id": results["ids"][0][i],
                "text": document,
                "score": round(similarity, 4),
                "document_id": metadata.get("doc_id", "unknown"),
                "filename": metadata.get("filename", "Unknown Document"),
                "page": metadata.get("page", 1),
                "chunk_index": metadata.get("chunk_index", 0),
                "file_type": metadata.get("file_type", "")
            })

        return retrieved_chunks

    def list_documents(self) -> List[Dict[str, Any]]:
        return list(self._load_registry().values())

    def get_stats(self) -> Dict[str, Any]:
        registry = self._load_registry()

        return {
            "total_documents": len(registry),
            "total_chunks": self.collection.count(),
            "embedding_provider": "gemini",
            "embedding_model": self.EMBEDDING_MODEL,
            "storage_path": str(self.chroma_dir)
        }


# Global singleton
vector_store_manager = VectorStoreManager()
