"""Data model for ByteIT file-class list responses."""

from dataclasses import dataclass
from typing import Any

from byteit.models.FileClass import FileClass


@dataclass
class FileClassList:
    """Collection of file classes with list metadata."""

    classes: list[FileClass]
    count: int
    detail: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileClassList":
        """Create a FileClassList instance from API response data."""
        classes_data = data.get("classes", []) or []
        classes = [FileClass.from_dict(class_data) for class_data in classes_data]
        return cls(
            classes=classes,
            count=data.get("count", len(classes)),
            detail=data.get("detail", ""),
        )
