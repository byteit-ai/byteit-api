"""Output format enumeration for document processing."""

from enum import Enum


class OutputFormat(str, Enum):
    """Supported output formats for document processing."""

    TXT = "txt"
    JSON = "json"
    HTML = "html"
    MD = "md"

    def __str__(self) -> str:
        """Return the string value of the format."""
        return self.value
