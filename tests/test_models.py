"""Tests for model classes."""

from datetime import datetime

import pytest

from byteit.models.DocumentMetadata import DocumentMetadata
from byteit.models.ExtractionType import ExtractionType
from byteit.models.JobList import JobList
from byteit.models.JobStatus import JobStatus
from byteit.models.ParseJob import ParseJob
from byteit.models.ProcessingOptions import ProcessingOptions


class TestParseJob:
    """Test ParseJob model."""

    def test_job_properties(self):
        """Job status properties work correctly."""
        job_completed = ParseJob(
            id="job_1",
            processing_status="completed",
            result_format="txt",
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        assert job_completed.is_completed is True
        assert job_completed.is_failed is False
        assert job_completed.is_processing is False

        job_failed = ParseJob(
            id="job_2",
            processing_status="failed",
            result_format="txt",
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        assert job_failed.is_completed is False
        assert job_failed.is_failed is True
        assert job_failed.is_processing is False

        job_processing = ParseJob(
            id="job_3",
            processing_status="processing",
            result_format="txt",
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        assert job_processing.is_completed is False
        assert job_processing.is_failed is False
        assert job_processing.is_processing is True

    def test_job_from_dict(self):
        """ParseJob.from_dict creates ParseJob from API data."""
        data = {
            "id": "job_123",
            "name": "jobs/parse-jobs/job_123",
            "uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "create_time": "2024-01-01T12:00:00Z",
            "update_time": "2024-01-01T12:30:00Z",
            "processing_status": "completed",
            "result_format": "json",
            "processing_time_seconds": 12.5,
            "credits_cost": 4,
        }

        job = ParseJob.from_dict(data)

        assert job.id == "job_123"
        assert job.name == "jobs/parse-jobs/job_123"
        assert job.processing_status == "completed"
        assert job.result_format == "json"
        assert job.processing_time_seconds == 12.5
        assert job.credits_cost == 4
        assert isinstance(job.create_time, datetime)

    def test_job_status_from_dict(self):
        """JobStatus.from_dict creates status model from API data."""
        status = JobStatus.from_dict(
            {
                "progress": 45,
                "processing_status": "processing",
                "message": None,
            }
        )

        assert status.progress == 45
        assert status.is_processing is True


class TestJobList:
    """Test JobList model."""

    def test_job_list_creation(self):
        """JobList holds list of jobs."""
        job1 = ParseJob(
            id="job_1",
            processing_status="completed",
            result_format="txt",
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        job2 = ParseJob(
            id="job_2",
            processing_status="pending",
            result_format="json",
            create_time=datetime.now(),
            update_time=datetime.now(),
        )

        job_list = JobList(jobs=[job1, job2], count=2, detail="Success")

        assert len(job_list.jobs) == 2
        assert job_list.count == 2
        assert job_list.detail == "Success"

    def test_job_list_from_dict(self):
        """JobList.from_dict keeps collection metadata and jobs."""
        job_list = JobList.from_dict(
            {
                "name": "jobs/parse-jobs",
                "uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "create_time": "2024-01-01T12:00:00Z",
                "update_time": "2024-01-01T12:30:00Z",
                "detail": "Success",
                "count": 1,
                "parse_jobs": [
                    {
                        "id": "job_1",
                        "processing_status": "pending",
                        "result_format": "txt",
                    }
                ],
            }
        )

        assert job_list.name == "jobs/parse-jobs"
        assert job_list.count == 1
        assert job_list.jobs[0].id == "job_1"


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
        assert options.extraction_type is ExtractionType.AUTO

    def test_to_dict(self):
        """to_dict serializes options."""
        options = ProcessingOptions(
            languages=["en", "es"],
            page_range="1-5",
            extraction_type=ExtractionType.COMPLEX,
        )

        result = options.to_dict()

        assert result["languages"] == ["en", "es"]
        assert result["page_range"] == "1-5"
        assert result["extraction_type"] == "complex"

    def test_from_dict_parses_extraction_type(self):
        """from_dict converts extraction_type strings into enums."""
        options = ProcessingOptions.from_dict({"extraction_type": "complex"})

        assert options.extraction_type is ExtractionType.COMPLEX

    def test_invalid_extraction_type_raises_error(self):
        """Invalid extraction type values are rejected."""
        with pytest.raises(ValueError, match="Invalid extraction type"):
            ProcessingOptions(extraction_type="invalid")
