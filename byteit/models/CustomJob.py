"""Data model for ByteIT custom LLM jobs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CustomJob:
    """Custom LLM processing job.

    Represents a custom job in the ByteIT system, where one or more documents
    are processed with a plan-specific model using an optional schema and prompt.

    Attributes:
        id: Unique job identifier.
        processing_status: Current status (pending, processing, completed, failed).
        nickname: Optional user-supplied label for the job.
        created_at: Job creation timestamp.
        updated_at: Job last-update timestamp.
        processing_time_seconds: Wall-clock seconds spent processing, once done.
        credits_cost: Credits charged for this custom job.
        extraction_schema: Optional JSON schema sent with the job.
        user_prompt: Optional user prompt appended to the model request.
        file_names: Original filenames uploaded for the job.
        total_page_count: Total page count across uploaded documents.
        document_types: Detected document types for uploaded files.

    Properties:
        is_completed: True if the job finished successfully.
        is_failed: True if the job failed.
        is_processing: True if the job is currently being processed.
    """

    id: str
    processing_status: str
    nickname: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    processing_time_seconds: float | None = None
    credits_cost: float | None = None
    extraction_schema: dict[str, Any] | None = None
    user_prompt: str | None = None
    file_names: list[str] | None = None
    total_page_count: int | None = None
    document_types: list[str] | None = None

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
    def from_dict(cls, data: dict[str, Any]) -> "CustomJob":
        """Create a CustomJob instance from API response data."""
        job_id = data.get("id") or data.get("job_id")
        if not job_id:
            raise KeyError("Custom job response is missing required field: id")

        file_names = data.get("file_names")
        if file_names is not None and not isinstance(file_names, list):
            file_names = list(file_names)

        document_types = data.get("document_types")
        if document_types is not None and not isinstance(document_types, list):
            document_types = list(document_types)

        return cls(
            id=job_id,
            processing_status=data.get("processing_status")
            or data.get("status", "pending"),
            nickname=data.get("nickname"),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            processing_time_seconds=data.get("processing_time_seconds"),
            credits_cost=data.get("credits_cost"),
            extraction_schema=data.get("extraction_schema"),
            user_prompt=data.get("user_prompt"),
            file_names=file_names,
            total_page_count=data.get("total_page_count"),
            document_types=document_types,
        )


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO datetime string when present."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None
