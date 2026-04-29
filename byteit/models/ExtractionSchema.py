"""Base Pydantic model for defining ByteIT extraction schemas."""

from __future__ import annotations

from typing import Any

try:
    from pydantic import BaseModel, ConfigDict
except ImportError as exc:
    raise ImportError(
        "Pydantic is required for ExtractionSchema. "
        "Install it with: pip install byteit[extract]"
    ) from exc

_SCHEMA_KEYS_TO_REMOVE = frozenset({"title"})


class ExtractionSchema(BaseModel):
    """Base class for defining structured extraction schemas.

    Extend this class and declare fields with type annotations and
    ``Field(description=...)`` to specify what to extract from a document.
    All fields should be ``Optional`` (i.e. ``str | None``) so the model
    can return ``null`` when a value is absent.

    Example::

        from byteit import ExtractionSchema
        from pydantic import Field

        class InvoiceSchema(ExtractionSchema):
            invoice_number: str | None = Field(
                description="The invoice number or identifier."
            )
            total_amount: str | None = Field(
                description="The total amount due on the invoice."
            )

        result = client.extract("parse_job_id", InvoiceSchema)
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def build_api_schema(cls) -> dict[str, Any]:
        """Build the pruned JSON schema dict to send to the ByteIT API.

        Returns:
            A JSON-serialisable dict representing the schema for this model.
        """
        raw_schema = cls.model_json_schema(by_alias=True)
        return _prune_schema_metadata(raw_schema)


def _prune_schema_metadata(value: object) -> Any:
    """Remove non-essential metadata keys from a nested JSON schema object."""
    if isinstance(value, dict):
        return {
            key: _prune_schema_metadata(child)
            for key, child in value.items()
            if key not in _SCHEMA_KEYS_TO_REMOVE
        }
    if isinstance(value, list):
        return [_prune_schema_metadata(item) for item in value]
    return value
