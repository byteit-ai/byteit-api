"""Data model for ByteIT Document Metadatata."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentMetadata:
    """Metadata information about a document."""

    original_filename: str
    document_type: str
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    language: str = "en"
    encoding: str = "utf-8"
