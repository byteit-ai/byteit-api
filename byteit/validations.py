"""Validation utilities for ByteIT API requests."""

from typing import Any

from .exceptions import ValidationError

# Valid processing option fields accepted by the API.
VALID_PROCESSING_OPTIONS: set[str] = {
    "languages",
    "page_range",
    "image_annotations",
    "table_enrichment",
    "extraction_type",
}


def validate_processing_options(options: dict[str, Any]) -> None:
    """Validate processing options dictionary.

    The 'output_format' should be passed as a top-level parameter, not
    inside processing_options.

    Args:
        options: Processing options dictionary to validate

    Raises:
        ValidationError: If any unexpected or deprecated fields are found

    """
    unexpected_fields: list[str] = []

    for field in options:
        if field not in VALID_PROCESSING_OPTIONS:
            unexpected_fields.append(field)

    if unexpected_fields:
        valid_fields = ", ".join(sorted(VALID_PROCESSING_OPTIONS))
        unexpected = ", ".join(sorted(unexpected_fields))
        raise ValidationError(
            f"Unexpected processing option fields: {unexpected}. "
            f"Valid fields are: {valid_fields}"
        )
