"""Data model for ByteIT extraction jobs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ExtractJob:
    """Structured field extraction job.

    Represents a field-extraction job in the ByteIT system, which runs against
    the parsed output of an existing :class:`~byteit.models.ParseJob.ParseJob`.

    Attributes:
        id: Unique job identifier.
        processing_status: Current status (pending, processing, completed, failed).
        name: Backend resource name.
        uid: Backend UUID for the resource.
        create_time: Job creation timestamp.
        update_time: Last update timestamp.
        delete_time: Job deletion timestamp.
        input_storage_path: Storage path for the input (parsed) document.
        output_storage_path: Storage path for the extraction result.
        processing_error: Error message if the job failed.

    Properties:
        is_completed: True if the job finished successfully.
        is_failed: True if the job failed.
        is_processing: True if the job is currently being processed.
    """

    id: str
    processing_status: str
    name: str | None = None
    uid: str | None = None
    create_time: datetime | None = None
    update_time: datetime | None = None
    delete_time: datetime | None = None
    input_storage_path: str | None = None
    output_storage_path: str | None = None
    processing_error: str | None = None

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
    def from_dict(cls, data: dict[str, Any]) -> "ExtractJob":
        """Create an ExtractJob instance from API response data.

        Args:
            data: Raw API response dictionary.

        Returns:
            A populated ExtractJob instance.
        """
        return cls(
            id=data.get("id") or data.get("job_id", ""),
            processing_status=data.get("processing_status", "pending"),
            name=data.get("name"),
            uid=data.get("uid"),
            create_time=cls._parse_datetime(
                data.get("create_time") or data.get("created_at")
            ),
            update_time=cls._parse_datetime(
                data.get("update_time") or data.get("updated_at")
            ),
            delete_time=cls._parse_datetime(data.get("delete_time")),
            input_storage_path=data.get("input_storage_path"),
            output_storage_path=data.get("output_storage_path"),
            processing_error=data.get("processing_error"),
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse an ISO datetime string when present."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None
