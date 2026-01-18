"""Data model for ByteIT Job."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, cast
from byteit.models.DocumentMetadata import DocumentMetadata
from byteit.models.ProcessingOptions import ProcessingOptions


@dataclass
class Job:
    """Document processing job.

    Represents a document parsing job in the ByteIT system, tracking its
    status, configuration, and results.

    Attributes:
        id: Unique job identifier
        created_at: Job creation timestamp
        updated_at: Last update timestamp
        processing_status: Current status (pending, processing, completed, failed)
        result_format: Output format (txt, json, md, html)
        owner_user_id: ID of the user who created the job
        file_data: Original file information
        file_hash: Hash of the input file
        nickname: Optional user-defined job name
        metadata: Document metadata (filename, type, pages, etc.)
        processing_options: Job configuration options
        processing_error: Error message if job failed
        storage_path: Internal storage location
        result_path: Path to processed result
        input_connector: Type of input connector used
        input_connection_data: Input connector configuration
        output_connector: Type of output connector used
        output_connection_data: Output connector configuration
        started_processing_at: Processing start time
        finished_processing_at: Processing completion time

    Properties:
        is_completed: True if job finished successfully
        is_failed: True if job failed
        is_processing: True if job is currently being processed
    """

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
    processing_options: Optional[ProcessingOptions] = None
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
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            created_at = datetime.now()  # fallback

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
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
            metadata_dict = cast(Dict[str, Any], data["metadata"])
            try:
                metadata = DocumentMetadata(
                    original_filename=metadata_dict.get("original_filename", ""),
                    document_type=metadata_dict.get("document_type", ""),
                    page_count=metadata_dict.get("page_count"),
                    language=metadata_dict.get("language", "en"),
                    encoding=metadata_dict.get("encoding", "utf-8"),
                )
            except Exception as e:
                # If metadata parsing fails, skip it
                print(f"Warning: Failed to parse metadata: {e}")
                metadata = None

        # Parse processing options
        processing_options = None
        processing_options_data = data.get("processing_options")
        if processing_options_data and isinstance(processing_options_data, dict):
            processing_options = ProcessingOptions.from_dict(processing_options_data)

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
