"""Processing options model for document processing."""

from dataclasses import dataclass, field
from typing import Any

from byteit.models.ParseType import ParseType


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
        image_annotations: Enable image annotation extraction
        force_image_annotations: Force image annotation extraction even when
            image is detected as useless
        table_enrichment: Enable table enrichment
        parse_type: Parse mode used by the backend parser
    """

    languages: list[str] = field(default_factory=_default_list)
    page_range: str = field(default="")
    image_annotations: bool = field(default=False)
    force_image_annotations: bool = field(default=False)
    table_enrichment: bool = field(default=False)
    parse_type: ParseType | str = field(default=ParseType.AUTO)

    @staticmethod
    def _parse_parse_type(
        parse_type: ParseType | str,
    ) -> ParseType:
        """Parse parse type into an enum value."""
        if isinstance(parse_type, ParseType):
            return parse_type

        normalized_parse_type = parse_type.lower()
        for value in ParseType:
            if value.value == normalized_parse_type:
                return value

        raise ValueError(f"Invalid parse type: {parse_type}")

    def __post_init__(self) -> None:
        """Normalize processing option values after initialization."""
        self.parse_type = self._parse_parse_type(self.parse_type)

        if self.force_image_annotations:
            self.image_annotations = True

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

        if self.force_image_annotations:
            result["force_image_annotations"] = self.force_image_annotations

        if self.table_enrichment:
            result["table_enrichment"] = self.table_enrichment

        result["parse_type"] = self.parse_type.value

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
        force_image_annotations = data.get("force_image_annotations", False)
        table_enrichment = data.get("table_enrichment", False)
        parse_type = data.get("parse_type", ParseType.AUTO)

        return cls(
            languages=languages,
            page_range=page_range,
            image_annotations=image_annotations,
            force_image_annotations=force_image_annotations,
            table_enrichment=table_enrichment,
            parse_type=parse_type,
        )
