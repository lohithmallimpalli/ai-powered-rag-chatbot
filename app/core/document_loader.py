import os
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
import docx
from app.config import settings

class DocumentExtractionError(Exception):
    """Custom exception raised when document extraction fails."""
    pass

class DocumentLoader:
    """
    Robust multi-format document parser supporting PDF, DOCX, and TXT
    with metadata preservation and page/section tracking.
    """

    @staticmethod
    def format_file_size(size_in_bytes: int) -> str:
        """Converts raw bytes to human-readable size string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.1f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.1f} TB"

    @classmethod
    def validate_file(cls, filename: str, file_size: int) -> Tuple[bool, str]:
        """
        Validate file extension and file size.
        Returns (is_valid, error_message).
        """
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file type '{ext}'. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            return False, f"File size ({cls.format_file_size(file_size)}) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        
        if file_size == 0:
            return False, "File is empty (0 bytes)."
            
        return True, ""

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Cleans extracted text by standardizing whitespace and removing control characters."""
        if not text:
            return ""
        # Remove null characters and non-printable control chars except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Normalize multiple spaces (keep newlines for paragraph breaks)
        text = re.sub(r'[ \t]+', ' ', text)
        # Collapse 3 or more newlines into 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @classmethod
    def load_document(cls, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extracts content from a file and returns a list of page/section items:
        [
            {
                "text": "...",
                "page": 1,
                "filename": "report.pdf",
                "file_type": ".pdf"
            },
            ...
        ]
        """
        ext = file_path.suffix.lower()
        filename = file_path.name
        
        if not file_path.exists():
            raise DocumentExtractionError(f"File not found: {file_path}")

        try:
            if ext == ".pdf":
                return cls._load_pdf(file_path, filename)
            elif ext == ".docx":
                return cls._load_docx(file_path, filename)
            elif ext == ".txt":
                return cls._load_txt(file_path, filename)
            else:
                raise DocumentExtractionError(f"Unsupported file format: {ext}")
        except Exception as e:
            if isinstance(e, DocumentExtractionError):
                raise
            raise DocumentExtractionError(f"Failed to parse document '{filename}': {str(e)}")

    @classmethod
    def _load_pdf(cls, file_path: Path, filename: str) -> List[Dict[str, Any]]:
        pages = []
        try:
            reader = PdfReader(str(file_path))
            total_pages = len(reader.pages)
            if total_pages == 0:
                raise DocumentExtractionError("PDF file has 0 pages.")

            for page_idx, page in enumerate(reader.pages):
                raw_text = page.extract_text() or ""
                cleaned = cls.clean_text(raw_text)
                if cleaned:
                    pages.append({
                        "text": cleaned,
                        "page": page_idx + 1,
                        "filename": filename,
                        "file_type": ".pdf",
                        "total_pages": total_pages
                    })
        except Exception as e:
            raise DocumentExtractionError(f"Error reading PDF '{filename}': {str(e)}")
            
        if not pages:
            raise DocumentExtractionError(f"No extractable text found in PDF '{filename}'. It may be a scanned or image-only document.")
        return pages

    @classmethod
    def _load_docx(cls, file_path: Path, filename: str) -> List[Dict[str, Any]]:
        try:
            doc = docx.Document(str(file_path))
            full_text = []
            
            # Extract paragraphs
            for para in doc.paragraphs:
                cleaned = cls.clean_text(para.text)
                if cleaned:
                    full_text.append(cleaned)
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_data = [cls.clean_text(cell.text) for cell in row.cells if cls.clean_text(cell.text)]
                    if row_data:
                        full_text.append(" | ".join(row_data))
                        
            combined = "\n\n".join(full_text)
            if not combined.strip():
                raise DocumentExtractionError(f"DOCX '{filename}' contains no readable text content.")
                
            return [{
                "text": combined,
                "page": 1,
                "filename": filename,
                "file_type": ".docx",
                "total_pages": 1
            }]
        except Exception as e:
            raise DocumentExtractionError(f"Error reading DOCX '{filename}': {str(e)}")

    @classmethod
    def _load_txt(cls, file_path: Path, filename: str) -> List[Dict[str, Any]]:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        content = None
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
                
        if content is None:
            raise DocumentExtractionError(f"Could not decode text file '{filename}' with supported encodings.")
            
        cleaned = cls.clean_text(content)
        if not cleaned:
            raise DocumentExtractionError(f"Text file '{filename}' is empty.")
            
        return [{
            "text": cleaned,
            "page": 1,
            "filename": filename,
            "file_type": ".txt",
            "total_pages": 1
        }]
