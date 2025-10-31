"""Data models for ByteIT API responses."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class DocumentMetadata:
    """Metadata information about a document."""

    original_filename: str
    document_type: str
    file_size_bytes: Optional[int] = None
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
    nickname: Optional[str] = None
    metadata: Optional[DocumentMetadata] = None
    processing_options: Optional[Dict[str, Any]] = None
    processing_error: Optional[str] = None
    storage_path: Optional[str] = None
    result_path: Optional[str] = None
    input_connector: Optional[str] = None
    input_connection_data: Optional[Dict[str, Any]] = None
    output_connector: Optional[str] = None
    output_connection_data: Optional[Dict[str, Any]] = None
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
        else:
            created_at = datetime.now()  # fallback

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(
                updated_at.replace("Z", "+00:00")
            )
        else:
            updated_at = datetime.now()  # fallback

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
        if data.get("metadata") and isinstance(data["metadata"], dict):
            metadata_dict = data["metadata"]
            try:
                metadata = DocumentMetadata(
                    original_filename=metadata_dict.get(
                        "original_filename", ""
                    ),
                    document_type=metadata_dict.get("document_type", ""),
                    file_size_bytes=metadata_dict.get("file_size_bytes"),
                    page_count=metadata_dict.get("page_count"),
                    language=metadata_dict.get("language", "en"),
                    encoding=metadata_dict.get("encoding", "utf-8"),
                )
            except Exception as e:
                # If metadata parsing fails, skip it
                print(f"Warning: Failed to parse metadata: {e}")
                metadata = None

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
            nickname=data.get("nickname"),
            metadata=metadata,
            processing_options=processing_options,
            processing_error=data.get("processing_error"),
            storage_path=data.get("storage_path"),
            result_path=data.get("result_path"),
            input_connector=data.get("input_connector"),
            input_connection_data=data.get("input_connection_data"),
            output_connector=data.get("output_connector"),
            output_connection_data=data.get("output_connection_data"),
            started_processing_at=started_processing_at,
            finished_processing_at=finished_processing_at,
        )


@dataclass
class JobList:
    """List of jobs with metadata."""

    jobs: list[Job]
    count: int
    detail: str
