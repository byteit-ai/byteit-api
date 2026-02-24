"""Processing options model for document processing."""

from dataclasses import dataclass, field
from typing import Any

from byteit.models.OutputFormat import OutputFormat


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
        output_format: Desired output format (txt, json, html, md)

    Note:
        The output_format is extracted and sent separately in API requests,
        while languages and page_range are sent as processing_options.
    """

    languages: list[str] = field(default_factory=_default_list)
    page_range: str = field(default="")
    output_format: OutputFormat | str = OutputFormat.TXT

    def __post_init__(self) -> None:
        """Validate and convert processing options."""
        # Convert string to OutputFormat if necessary
        if isinstance(self.output_format, str):
            try:
                object.__setattr__(
                    self, "output_format", OutputFormat(self.output_format)
                )
            except ValueError as exc:
                raise ValueError(
                    f"Invalid output format: {self.output_format}. "
                    f"Valid formats are: txt, json, html, md"
                ) from exc

    def to_dict(self) -> dict[str, Any]:
        """Convert ProcessingOptions to dictionary for API communication.

        Note: output_format is included here but will be extracted by the
        API client and sent as a top-level parameter.

        Returns:
            Dictionary representation suitable for API requests
        """
        result: dict[str, Any] = {}

        if self.languages:
            result["languages"] = self.languages

        if self.page_range:
            result["page_range"] = self.page_range

        # Include output_format for extraction by API client
        if isinstance(self.output_format, OutputFormat):
            result["output_format"] = self.output_format.value
        else:
            result["output_format"] = str(self.output_format)

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
        output_format_str = data.get("output_format", "txt")

        # Convert output_format to enum
        output_format = OutputFormat(output_format_str)

        return cls(
            languages=languages,
            page_range=page_range,
            output_format=output_format,
        )
