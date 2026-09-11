"""Data model for ByteIT file classification labels."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class FileClass:
    """Classification label with a description used by the classifier.

    Represents either a system default document class or a user-saved label.
    """

    label: str
    description: str
    id: str | None = None
    scope: str | None = None
    create_time: datetime | None = None

    def to_api_dict(self) -> dict[str, str]:
        """Return the label/description payload accepted by classification APIs."""
        return {
            "label": self.label,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileClass":
        """Create a FileClass instance from API response data."""
        label = data.get("label")
        if not isinstance(label, str) or not label:
            raise KeyError("File class response is missing required field: label")

        description = data.get("description")
        if not isinstance(description, str):
            raise KeyError("File class response is missing required field: description")

        class_id = data.get("id")
        if class_id is not None and not isinstance(class_id, str):
            class_id = str(class_id)

        scope = data.get("scope")
        if scope is not None and not isinstance(scope, str):
            scope = str(scope)

        return cls(
            label=label,
            description=description,
            id=class_id,
            scope=scope,
            create_time=_parse_datetime(data.get("create_time")),
        )


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO datetime string when present."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None
