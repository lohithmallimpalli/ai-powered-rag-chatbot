from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import settings

class DocumentChunker:
    """
    Splits extracted document pages into semantically coherent chunks
    with complete metadata preservation for source attribution.
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""]
        )

    def chunk_document_pages(
        self, 
        doc_id: str, 
        pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Takes raw page objects and outputs chunk objects ready for embedding:
        [
            {
                "chunk_id": "doc123_chunk_0",
                "doc_id": "doc123",
                "text": "...",
                "metadata": {
                    "doc_id": "doc123",
                    "filename": "file.pdf",
                    "page": 1,
                    "chunk_index": 0,
                    "file_type": ".pdf"
                }
            },
            ...
        ]
        """
        all_chunks = []
        global_chunk_idx = 0

        for page_data in pages:
            raw_text = page_data.get("text", "")
            page_num = page_data.get("page", 1)
            filename = page_data.get("filename", "unknown")
            file_type = page_data.get("file_type", ".txt")

            if not raw_text.strip():
                continue

            sub_chunks = self.splitter.split_text(raw_text)

            for sub_text in sub_chunks:
                clean_chunk_text = sub_text.strip()
                # Filter out trivial fragments (e.g. single punctuation or < 15 chars)
                if len(clean_chunk_text) < 15:
                    continue

                chunk_obj = {
                    "chunk_id": f"{doc_id}_chunk_{global_chunk_idx}",
                    "doc_id": doc_id,
                    "text": clean_chunk_text,
                    "metadata": {
                        "doc_id": doc_id,
                        "filename": filename,
                        "page": int(page_num),
                        "chunk_index": global_chunk_idx,
                        "file_type": file_type
                    }
                }
                all_chunks.append(chunk_obj)
                global_chunk_idx += 1

        return all_chunks
