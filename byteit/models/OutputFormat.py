"""Output format enumeration for document processing."""

from enum import StrEnum


class OutputFormat(StrEnum):
    """Supported output formats for document processing."""

    TXT = "txt"
    JSON = "json"
    HTML = "html"
    MD = "md"
    EXCEL = "zip"
    ZIP = "zip"

    def __str__(self) -> str:
        """Return the string value of the format."""
        return self.value
