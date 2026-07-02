"""Document type value object."""

from enum import Enum


class DocumentType(str, Enum):  # noqa: UP042
    """Supported document types for ByteIT uploads.

    Mirrors the backend ``DocumentType`` enum in saint-mary. Use
    :meth:`is_supported_extension` when filtering local files for upload.
    """

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    XML = "xml"
    PPTX = "pptx"
    XLSX = "xlsx"
    XLS = "xls"
    MD = "md"
    HTML = "html"
    JSON = "json"
    JPEG = "jpeg"
    PNG = "png"
    JPG = "jpg"
    TIFF = "tiff"
    BMP = "bmp"

    @classmethod
    def supported_extensions(cls) -> frozenset[str]:
        """Return the set of file extensions accepted for upload."""
        return frozenset(member.value for member in cls)

    @classmethod
    def is_supported_extension(cls, extension: str) -> bool:
        """Return True when *extension* maps to a supported document type."""
        return extension.lstrip(".").lower() in cls.supported_extensions()
