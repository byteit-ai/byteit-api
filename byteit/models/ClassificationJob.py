"""Data model for ByteIT classification jobs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ClassificationJob:
    """Document classification job.

    Represents a user-requested classification job that assigns a document
    class label based on system defaults or caller-provided class definitions.

    Attributes:
        id: Unique public job identifier.
        processing_status: Current status (pending, processing, completed, failed).
        nickname: Optional user-supplied label for the job.
        document_class: Predicted top-level document class once completed.
        is_internal: Whether the job was created by an internal pipeline.
        created_at: Job creation timestamp.
        updated_at: Job last-update timestamp.
        processing_time_seconds: Wall-clock seconds spent processing, once done.
        credits_cost: Credits charged for this classification job.
    """

    id: str
    processing_status: str
    nickname: str | None = None
    document_class: str | None = None
    is_internal: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    processing_time_seconds: float | None = None
    credits_cost: float | None = None

    @property
    def is_completed(self) -> bool:
        """Check if the job is completed."""
        return self.processing_status == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if the job failed."""
        return self.processing_status == "failed"

    @property
    def is_processing(self) -> bool:
        """Check if the job is currently processing."""
        return self.processing_status in ("pending", "processing")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassificationJob":
        """Create a ClassificationJob instance from API response data."""
        job_id = data.get("id") or data.get("job_id")
        if not job_id:
            raise KeyError("Classification job response is missing required field: id")

        return cls(
            id=job_id,
            processing_status=data.get("processing_status")
            or data.get("status", "pending"),
            nickname=data.get("nickname"),
            document_class=data.get("document_class"),
            is_internal=bool(data.get("is_internal", False)),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            processing_time_seconds=data.get("processing_time_seconds"),
            credits_cost=data.get("credits_cost"),
        )


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO datetime string when present."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None
