"""Tests for model classes."""

from datetime import datetime
import pytest

from byteit.models.Job import Job
from byteit.models.JobList import JobList
from byteit.models.DocumentMetadata import DocumentMetadata
from byteit.models.ProcessingOptions import ProcessingOptions


class TestJob:
    """Test Job model."""

    def test_job_properties(self):
        """Job status properties work correctly."""
        job_completed = Job(
            id="job_1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            processing_status="completed",
            result_format="txt",
        )
        assert job_completed.is_completed is True
        assert job_completed.is_failed is False
        assert job_completed.is_processing is False

        job_failed = Job(
            id="job_2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            processing_status="failed",
            result_format="txt",
        )
        assert job_failed.is_completed is False
        assert job_failed.is_failed is True
        assert job_failed.is_processing is False

        job_processing = Job(
            id="job_3",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            processing_status="processing",
            result_format="txt",
        )
        assert job_processing.is_completed is False
        assert job_processing.is_failed is False
        assert job_processing.is_processing is True

    def test_job_from_dict(self):
        """Job.from_dict creates Job from API data."""
        data = {
            "id": "job_123",
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:30:00Z",
            "processing_status": "completed",
            "result_format": "json",
        }

        job = Job.from_dict(data)

        assert job.id == "job_123"
        assert job.processing_status == "completed"
        assert job.result_format == "json"
        assert isinstance(job.created_at, datetime)


class TestJobList:
    """Test JobList model."""

    def test_job_list_creation(self):
        """JobList holds list of jobs."""
        job1 = Job(
            id="job_1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            processing_status="completed",
            result_format="txt",
        )
        job2 = Job(
            id="job_2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            processing_status="pending",
            result_format="json",
        )

        job_list = JobList(jobs=[job1, job2], count=2, detail="Success")

        assert len(job_list.jobs) == 2
        assert job_list.count == 2
        assert job_list.detail == "Success"


class TestDocumentMetadata:
    """Test DocumentMetadata model."""

    def test_metadata_creation(self):
        """DocumentMetadata stores document info."""
        metadata = DocumentMetadata(
            original_filename="test.pdf",
            document_type="pdf",
            page_count=10,
            language="en",
            encoding="utf-8",
        )

        assert metadata.original_filename == "test.pdf"
        assert metadata.document_type == "pdf"
        assert metadata.page_count == 10
        assert metadata.language == "en"
        assert metadata.encoding == "utf-8"

    def test_metadata_defaults(self):
        """DocumentMetadata uses correct defaults."""
        metadata = DocumentMetadata(original_filename="doc.pdf", document_type="pdf")

        assert metadata.language == "en"
        assert metadata.encoding == "utf-8"
        assert metadata.page_count is None


class TestProcessingOptions:
    """Test ProcessingOptions model."""

    def test_default_options(self):
        """ProcessingOptions has correct defaults."""
        options = ProcessingOptions()

        assert options.languages == ["en"]
        assert options.page_range == ""

    def test_to_dict(self):
        """to_dict serializes options."""
        options = ProcessingOptions(languages=["en", "es"], page_range="1-5")

        result = options.to_dict()

        assert result["languages"] == ["en", "es"]
        assert result["page_range"] == "1-5"
