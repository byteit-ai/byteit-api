"""Data model for ByteIT extraction jobs."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ExtractJob:
    """Structured field extraction job.

    Represents a field-extraction job in the ByteIT system, which runs against
    the parsed output of an existing :class:`~byteit.models.ParseJob.ParseJob`.

    Attributes:
        id: Unique job identifier.
        processing_status: Current status (pending, processing, completed, failed).
        input_job_id: ID of the parse job this extraction was created from.
        nickname: Optional user-supplied label for the job.
        processing_time_seconds: Wall-clock seconds spent processing, once done.
        credits_cost: Credits charged for this extraction job.
        extraction_schema: The JSON schema dict sent to the extractor.
        extraction_complexity: Complexity tier (low, medium, high).

    Properties:
        is_completed: True if the job finished successfully.
        is_failed: True if the job failed.
        is_processing: True if the job is currently being processed.
    """

    id: str
    processing_status: str
    input_job_id: str | None = None
    nickname: str | None = None
    processing_time_seconds: float | None = None
    credits_cost: float | None = None
    extraction_schema: dict[str, Any] | None = None
    extraction_complexity: str | None = None

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
        job_id = data.get("id") or data.get("job_id")
        if not job_id:
            raise KeyError("Extract job response is missing required field: id")

        return cls(
            id=job_id,
            processing_status=data.get("processing_status", "pending"),
            input_job_id=data.get("input_job_id"),
            nickname=data.get("nickname"),
            processing_time_seconds=data.get("processing_time_seconds"),
            credits_cost=data.get("credits_cost"),
            extraction_schema=data.get("extraction_schema"),
            extraction_complexity=data.get("extraction_complexity"),
        )
