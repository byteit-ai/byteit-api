"""Validation utilities for ByteIT API requests."""

from typing import Any, Dict, List, Set

from .exceptions import ValidationError


# Valid processing option fields (only languages and page_range are allowed)
VALID_PROCESSING_OPTIONS: Set[str] = {
    "languages",
    "page_range",
}


def validate_processing_options(options: Dict[str, Any]) -> None:
    """
    Validate processing options dictionary.

    Only 'languages' and 'page_range' are allowed in processing_options.
    The 'output_format' should be passed as a top-level parameter, not
    inside processing_options.

    Args:
        options: Processing options dictionary to validate

    Raises:
        ValidationError: If any unexpected or deprecated fields are found

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
