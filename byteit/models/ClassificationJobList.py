"""Data model for ByteIT classification job list responses."""

from dataclasses import dataclass
from typing import Any

from byteit.models.ClassificationJob import ClassificationJob


@dataclass
class ClassificationJobList:
    """Collection of classification jobs with metadata.

    Returned by the list-classification-jobs endpoint.

    Attributes:
        jobs: List of ClassificationJob objects.
        count: Total number of classification jobs returned.
        detail: Additional information or messages from the API.
    """

    jobs: list[ClassificationJob]
    count: int
    detail: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassificationJobList":
        """Create a ClassificationJobList instance from API response data."""
        jobs_data = data.get("classification_jobs", []) or []
        jobs = [ClassificationJob.from_dict(job_data) for job_data in jobs_data]
        return cls(
            jobs=jobs,
            count=data.get("count", len(jobs)),
            detail=data.get("detail", ""),
        )
