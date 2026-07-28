"""Data model for ByteIT saved schema list responses."""

from dataclasses import dataclass
from typing import Any

from byteit.models.SavedSchema import SavedSchema


@dataclass
class SavedSchemaList:
    """Collection of saved schemas with list metadata."""

    schemas: list[SavedSchema]
    count: int
    detail: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SavedSchemaList":
        """Create a SavedSchemaList instance from API response data."""
        schemas_data = data.get("schemas", []) or []
        schemas = [SavedSchema.from_dict(schema_data) for schema_data in schemas_data]
        return cls(
            schemas=schemas,
            count=data.get("count", len(schemas)),
            detail=data.get("detail", ""),
        )
