"""Data models for ByteIT API responses."""

from dataclasses import dataclass
from byteit.models.Job import Job


@dataclass
class JobList:
    """Collection of jobs with metadata.

    Returned by list operations containing multiple jobs.

    Attributes:
        jobs: List of Job objects
        count: Total number of jobs
        detail: Additional information or messages
    """

    jobs: list[Job]
    count: int
    detail: str
