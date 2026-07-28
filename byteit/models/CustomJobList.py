"""Data model for ByteIT custom job list responses."""

from dataclasses import dataclass
from typing import Any

from byteit.models.CustomJob import CustomJob


@dataclass
class CustomJobList:
    """Collection of custom jobs with metadata.

    Returned by the list-custom-jobs endpoint.

    Attributes:
        jobs: List of CustomJob objects.
        count: Total number of custom jobs returned.
        detail: Additional information or messages from the API.
    """

    jobs: list[CustomJob]
    count: int
    detail: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomJobList":
        """Create a CustomJobList instance from API response data."""
        jobs_data = data.get("custom_jobs", []) or []
        jobs = [CustomJob.from_dict(job_data) for job_data in jobs_data]
        return cls(
            jobs=jobs,
            count=data.get("count", len(jobs)),
            detail=data.get("detail", ""),
        )
