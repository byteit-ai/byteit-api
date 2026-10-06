"""Data model for ByteIT document-class list responses."""

from dataclasses import dataclass
from typing import Any

from byteit.models.DocumentClass import DocumentClass


@dataclass
class DocumentClassList:
    """Collection of document classes with list metadata."""

    classes: list[DocumentClass]
    count: int
    detail: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentClassList":
        """Create a DocumentClassList instance from API response data."""
        classes_data = data.get("classes", []) or []
        classes = [DocumentClass.from_dict(class_data) for class_data in classes_data]
        return cls(
            classes=classes,
            count=data.get("count", len(classes)),
            detail=data.get("detail", ""),
        )
