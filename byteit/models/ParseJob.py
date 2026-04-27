"""Data model for ByteIT parse jobs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from byteit.models.DocumentMetadata import DocumentMetadata
from byteit.models.ProcessingOptions import ProcessingOptions


@dataclass
class ParseJob:
    """Document processing parse job.

    Represents a document parsing job in the ByteIT system, tracking its
    status, configuration, and results.

    Attributes:
        id: Unique job identifier
        name: Backend resource name
        uid: Backend UUID for the resource
        create_time: Job creation timestamp
        update_time: Last update timestamp
        delete_time: Job deletion timestamp
        processing_status: Current status (pending, processing, completed, failed)
        result_format: Output format (txt, json, md, html)
        nickname: Optional user-defined job name
        metadata: Document metadata (filename, type, pages, etc.)
        processing_options: Job configuration options
        processing_time_seconds: Total processing time reported by backend
        processing_error: Error message if job failed
        credits_cost: Credits consumed by this job
        input_connector: Type of input connector used
        output_connector: Type of output connector used

    Properties:
        is_completed: True if job finished successfully
        is_failed: True if job failed
        is_processing: True if job is currently being processed
    """

    id: str
    processing_status: str
    result_format: str
    name: str | None = None
    uid: str | None = None
    create_time: datetime | None = None
    update_time: datetime | None = None
    delete_time: datetime | None = None
    nickname: str | None = None
    metadata: DocumentMetadata | None = None
    processing_options: ProcessingOptions | None = None
    processing_time_seconds: float | None = None
    processing_error: str | None = None
    credits_cost: int | float | None = None
    input_connector: str | None = None
    output_connector: str | None = None

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
    def from_dict(cls, data: dict[str, Any]) -> "ParseJob":
        """Create a ParseJob instance from API response data."""
        create_time = cls._parse_datetime(data.get("create_time", data.get("created_at")))
        update_time = cls._parse_datetime(data.get("update_time", data.get("updated_at")))
        delete_time = cls._parse_datetime(data.get("delete_time"))

        metadata = None
        if data.get("metadata") and isinstance(data["metadata"], dict):
            metadata_dict = cast(dict[str, Any], data["metadata"])
            metadata = DocumentMetadata(
                original_filename=metadata_dict.get("original_filename") or "",
                document_type=metadata_dict.get("document_type") or "",
                page_count=metadata_dict.get("page_count"),
                language=metadata_dict.get("language", "en"),
                encoding=metadata_dict.get("encoding", "utf-8"),
            )

        processing_options = None
        processing_options_data = data.get("processing_options")
        if processing_options_data and isinstance(processing_options_data, dict):
            processing_options = ProcessingOptions.from_dict(processing_options_data)

        result_format = data.get("result_format")
        if not result_format and isinstance(processing_options_data, dict):
            result_format = processing_options_data.get("output_format", "")

        return cls(
            id=data["id"],
            processing_status=data["processing_status"],
            result_format=result_format or "",
            name=data.get("name"),
            uid=data.get("uid"),
            create_time=create_time,
            update_time=update_time,
            delete_time=delete_time,
            nickname=data.get("nickname"),
            metadata=metadata,
            processing_options=processing_options,
            processing_time_seconds=data.get("processing_time_seconds"),
            processing_error=data.get("processing_error"),
            credits_cost=data.get("credits_cost"),
            input_connector=data.get("input_connector"),
            output_connector=data.get("output_connector"),
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse an ISO datetime string when present."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None
