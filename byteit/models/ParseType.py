"""Document parse type value object."""

from enum import Enum


class ParseType(Enum):
    """Document parse type enumeration."""

    AUTO = "auto"
    COMPLEX = "complex"
    HANDWRITTEN = "handwritten"
