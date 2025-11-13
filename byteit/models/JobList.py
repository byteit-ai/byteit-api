"""Data models for ByteIT API responses."""

from dataclasses import dataclass
from Job import Job


@dataclass
class JobList:
    """List of jobs with metadata."""

    jobs: list[Job]
    count: int
    detail: str
