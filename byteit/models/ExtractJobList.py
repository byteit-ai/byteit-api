"""Data model for ByteIT extract job list responses."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from byteit.models.ExtractJob import ExtractJob


@dataclass
class ExtractJobList:
    """Collection of extract jobs with metadata.

    Returned by the list-extract-jobs endpoint.

    Attributes:
        jobs: List of ExtractJob objects.
        count: Total number of extract jobs returned.
        detail: Additional information or messages from the API.
        name: Backend resource name.
        uid: Backend UUID for the collection resource.
        create_time: Collection creation timestamp.
        update_time: Collection update timestamp.
        delete_time: Collection deletion timestamp.
    """

    jobs: list[ExtractJob]
    count: int
    detail: str
    name: str | None = None
    uid: str | None = None
    create_time: datetime | None = None
    update_time: datetime | None = None
    delete_time: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExtractJobList":
        """Create an ExtractJobList instance from API response data."""
        jobs_data = data.get("extract_jobs", []) or []
        jobs = [ExtractJob.from_dict(job_data) for job_data in jobs_data]
        return cls(
            jobs=jobs,
            count=data.get("count", len(jobs)),
            detail=data.get("detail", ""),
            name=data.get("name"),
            uid=data.get("uid"),
            create_time=_parse_datetime(data.get("create_time")),
            update_time=_parse_datetime(data.get("update_time")),
            delete_time=_parse_datetime(data.get("delete_time")),
        )


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO datetime string when present."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None
