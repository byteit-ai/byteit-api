"""Processing options model for document processing."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

from byteit.models.OutputFormat import OutputFormat


def _default_dict() -> Dict[str, Any]:
    """Factory function for default dictionary."""
    return {}


def _default_list() -> List[str]:
    """Factory function for default list."""
    return ["en"]


@dataclass
class ProcessingOptions:
    """Document processing options value object."""

    options: Dict[str, Any] = field(default_factory=_default_dict)
    ocr_model: str = field(default="")
    languages: List[str] = field(default_factory=_default_list)
    page_range: str = field(default="")
    output_format: Union[OutputFormat, str] = OutputFormat.TXT

    def __post_init__(self):
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

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ProcessingOptions to dictionary for API communication.

        Returns:
            Dictionary representation suitable for API requests
        """
        result: Dict[str, Any] = {}

        if self.ocr_model:
            result["ocr_model"] = self.ocr_model

        if self.languages:
            result["languages"] = self.languages

        if self.page_range:
            result["page_range"] = self.page_range

        # Always include output_format - ensure it's a string value
        if isinstance(self.output_format, OutputFormat):
            result["output_format"] = self.output_format.value
        else:
            result["output_format"] = str(self.output_format)

        # Merge any additional options
        if self.options:
            result.update(self.options)

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingOptions":
        """
        Create ProcessingOptions from dictionary.

        Args:
            data: Dictionary containing processing options

        Returns:
            ProcessingOptions instance
        """
        # Extract known fields
        ocr_model = data.get("ocr_model", "")
        languages = data.get("languages", [])
        page_range = data.get("page_range", "")
        output_format_str = data.get("output_format", "txt")

        # Convert output_format to enum
        output_format = OutputFormat(output_format_str)

        # Store remaining options
        known_keys = {
            "ocr_model",
            "languages",
            "page_range",
            "output_format",
        }
        options = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            options=options,
            ocr_model=ocr_model,
            languages=languages,
            page_range=page_range,
            output_format=output_format,
        )
