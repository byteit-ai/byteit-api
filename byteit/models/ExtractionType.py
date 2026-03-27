"""Document extraction type value object."""

from enum import Enum


class ExtractionType(Enum):
    """Document extraction type enumeration."""

    AUTO = "auto"
    COMPLEX = "complex"
