"""Data models for ByteIT API responses."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class DocumentMetadata:
    """Metadata information about a document."""

    original_filename: str
    document_type: str
    file_size_bytes: int
    page_count: Optional[int] = None
    language: str = "en"
    encoding: str = "utf-8"


@dataclass
class Job:
    """Represents a document processing job."""

    id: str
    created_at: datetime
    updated_at: datetime
    processing_status: str
    result_format: str
    owner_user_id: Optional[str] = None
    file_data: Optional[str] = None
    file_hash: Optional[str] = None
    metadata: Optional[DocumentMetadata] = None
    processing_options: Optional[Dict[str, Any]] = None
    processing_error: Optional[str] = None
    storage_path: Optional[str] = None
    result_path: Optional[str] = None
    started_processing_at: Optional[datetime] = None
    finished_processing_at: Optional[datetime] = None

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
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create a Job instance from API response data."""
        # Parse datetime fields
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(
                updated_at.replace("Z", "+00:00")
            )

        started_processing_at = data.get("started_processing_at")
        if isinstance(started_processing_at, str):
            started_processing_at = datetime.fromisoformat(
                started_processing_at.replace("Z", "+00:00")
            )

        finished_processing_at = data.get("finished_processing_at")
        if isinstance(finished_processing_at, str):
            finished_processing_at = datetime.fromisoformat(
                finished_processing_at.replace("Z", "+00:00")
            )

        # Parse metadata
        metadata = None
        if data.get("metadata"):
            metadata = DocumentMetadata(**data["metadata"])

        # Parse processing options (keep as dict)
        processing_options = data.get("processing_options")

        return cls(
            id=data["id"],
            created_at=created_at,
            updated_at=updated_at,
            processing_status=data["processing_status"],
            result_format=data["result_format"],
            owner_user_id=data.get("owner_user_id"),
            file_data=data.get("file_data"),
            file_hash=data.get("file_hash"),
            metadata=metadata,
            processing_options=processing_options,
            processing_error=data.get("processing_error"),
            storage_path=data.get("storage_path"),
            result_path=data.get("result_path"),
            started_processing_at=started_processing_at,
            finished_processing_at=finished_processing_at,
        )


@dataclass
class JobList:
    """List of jobs with metadata."""

    jobs: list[Job]
    count: int
    detail: str
