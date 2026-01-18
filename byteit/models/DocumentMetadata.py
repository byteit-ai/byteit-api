"""Data model for ByteIT Document Metadatata."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentMetadata:
    """Document metadata information.

    Contains information about the original document being processed.

    Attributes:
        original_filename: Original name of the uploaded file
        document_type: Type/format of document (pdf, docx, etc.)
        page_count: Number of pages in document (if applicable)
        language: Document language code (default: 'en')
        encoding: Character encoding (default: 'utf-8')
    """

    original_filename: str
    document_type: str
    page_count: Optional[int] = None
    language: str = "en"
    encoding: str = "utf-8"
