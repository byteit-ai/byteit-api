"""Data model for lightweight ByteIT job status responses."""

from dataclasses import dataclass
from typing import Any


@dataclass
class JobStatus:
    """Lightweight processing status for a job.

    Attributes:
        progress: Reported percentage progress from the backend.
        processing_status: Current backend status.
        message: Optional backend message, usually populated on failures.
    """

    progress: int | float | None = None
    processing_status: str = "unknown"
    message: str | None = None

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
    def from_dict(cls, data: dict[str, Any]) -> "JobStatus":
        """Create a JobStatus instance from API response data."""
        return cls(
            progress=data.get("progress"),
            processing_status=data.get("processing_status", "unknown"),
            message=data.get("message") or data.get("detail"),
        )
