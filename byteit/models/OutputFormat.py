"""Output format enumeration for document processing."""

from enum import Enum


class OutputFormat(str, Enum):  # noqa: UP042
    """Supported output formats for document processing."""

    TXT = "txt"
    JSON = "json"
    HTML = "html"
    MD = "md"
    EXCEL = "zip"

    def __str__(self) -> str:
        """Return the string value of the format."""
        return self.value
