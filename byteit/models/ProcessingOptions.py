"""Processing options model for document processing."""

from dataclasses import dataclass, field
from typing import Any


def _default_list() -> list[str]:
    """Factory function for default list."""
    return ["en"]


@dataclass
class ProcessingOptions:
    """Document processing configuration.

    Specifies how documents should be processed by ByteIT.

    Attributes:
        languages: List of language codes for OCR/parsing (default: ['en'])
        page_range: Specific pages to process (e.g., '1-5' or '1,3,5')
    """

    languages: list[str] = field(default_factory=_default_list)
    page_range: str = field(default="")
    image_annotations: bool = field(default=False)
    table_enrichment: bool = field(default=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert ProcessingOptions to dictionary for API communication.

        Returns:
            Dictionary representation suitable for API requests
        """
        result: dict[str, Any] = {}

        if self.languages:
            result["languages"] = self.languages

        if self.page_range:
            result["page_range"] = self.page_range

        if self.image_annotations:
            result["image_annotations"] = self.image_annotations

        if self.table_enrichment:
            result["table_enrichment"] = self.table_enrichment

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessingOptions":
        """Create ProcessingOptions from dictionary.

        Args:
            data: Dictionary containing processing options

        Returns:
            ProcessingOptions instance
        """
        languages = data.get("languages", ["en"])
        page_range = data.get("page_range", "")
        image_annotations = data.get("image_annotations", False)
        table_enrichment = data.get("table_enrichment", False)

        return cls(
            languages=languages,
            page_range=page_range,
            image_annotations=image_annotations,
            table_enrichment=table_enrichment,
        )
