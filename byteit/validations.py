"""Validation utilities for ByteIT API requests."""

from typing import Any, Dict, List, Set

from .exceptions import ValidationError


# Expected processing option fields
VALID_PROCESSING_OPTIONS: Set[str] = {
    "ocr_model",
    "languages",
    "page_range",
    "output_format",
}


def validate_processing_options(options: Dict[str, Any]) -> None:
    """
    Validate processing options dictionary.

    Args:
        options: Processing options dictionary to validate

    Raises:
        ValidationError: If any unexpected fields are found

    """
    unexpected_fields: List[str] = []
    for field in options.keys():
        if field not in VALID_PROCESSING_OPTIONS:
            unexpected_fields.append(field)

    if unexpected_fields:
        valid_fields = ", ".join(sorted(VALID_PROCESSING_OPTIONS))
        unexpected = ", ".join(sorted(unexpected_fields))
        raise ValidationError(
            f"Unexpected processing option fields: {unexpected}. "
            f"Valid fields are: {valid_fields}"
        )
