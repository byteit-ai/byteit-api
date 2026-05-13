"""Data model for ByteIT saved schemas."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass
class SavedSchema:
    """Saved extraction schema owned by the authenticated user."""

    name: str
    schema_json: dict[str, Any]

    def build_api_schema(self) -> dict[str, Any]:
        """Return a JSON-schema payload compatible with extract-job methods."""
        return deepcopy(self.schema_json)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SavedSchema":
        """Create a SavedSchema instance from API response data."""
        name = data.get("name")
        if not isinstance(name, str) or not name:
            raise KeyError("Saved schema response is missing required field: name")

        schema_json = data.get("schema_json")
        if not isinstance(schema_json, dict):
            raise KeyError("Saved schema response is missing required field: schema_json")

        return cls(name=name, schema_json=schema_json)
