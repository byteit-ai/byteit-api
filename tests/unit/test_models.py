"""Tests for model classes."""

import pytest

from byteit.models.ClassificationJob import ClassificationJob
from byteit.models.ClassificationJobList import ClassificationJobList
from byteit.models.DocumentMetadata import DocumentMetadata
from byteit.models.FileClass import FileClass
from byteit.models.FileClassList import FileClassList
from byteit.models.JobList import JobList
from byteit.models.JobStatus import JobStatus
from byteit.models.ParseJob import ParseJob
from byteit.models.ParseType import ParseType
from byteit.models.ProcessingOptions import ProcessingOptions
from byteit.models.SavedSchema import SavedSchema
from byteit.models.SavedSchemaList import SavedSchemaList


class TestParseJob:
    """Test ParseJob model."""

    def test_job_properties(self):
        """Job status properties work correctly."""
        job_completed = ParseJob(
            id="job_1",
            processing_status="completed",
            result_format="txt",
        )
        assert job_completed.is_completed is True
        assert job_completed.is_failed is False
        assert job_completed.is_processing is False

        job_failed = ParseJob(
            id="job_2",
            processing_status="failed",
            result_format="txt",
        )
        assert job_failed.is_completed is False
        assert job_failed.is_failed is True
        assert job_failed.is_processing is False

        job_processing = ParseJob(
            id="job_3",
            processing_status="processing",
            result_format="txt",
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
        assert job.processing_status == "completed"
        assert job.result_format == "json"
        assert job.processing_time_seconds == 12.5
        assert job.credits_cost == 4

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
        )
        job2 = ParseJob(
            id="job_2",
            processing_status="pending",
            result_format="json",
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
        assert options.parse_type is ParseType.AUTO

    def test_to_dict(self):
        """to_dict serializes options."""
        options = ProcessingOptions(
            languages=["en", "es"],
            page_range="1-5",
            parse_type=ParseType.COMPLEX,
        )

        result = options.to_dict()

        assert result["languages"] == ["en", "es"]
        assert result["page_range"] == "1-5"
        assert result["parse_type"] == "complex"

    def test_from_dict_parses_parse_type(self):
        """from_dict converts parse_type strings into enums."""
        options = ProcessingOptions.from_dict({"parse_type": "complex"})

        assert options.parse_type is ParseType.COMPLEX

    def test_force_image_annotations_enables_image_annotations(self):
        """force_image_annotations implies image_annotations."""
        options = ProcessingOptions(force_image_annotations=True)

        assert options.force_image_annotations is True
        assert options.image_annotations is True
        assert options.to_dict()["force_image_annotations"] is True
        assert options.to_dict()["image_annotations"] is True

    def test_accepts_handwritten_parse_type(self):
        """HANDWRITTEN is a valid parse type."""
        options = ProcessingOptions(parse_type="handwritten")

        assert options.parse_type is ParseType.HANDWRITTEN

    def test_invalid_parse_type_raises_error(self):
        """Invalid parse type values are rejected."""
        with pytest.raises(ValueError, match="Invalid parse type"):
            ProcessingOptions(parse_type="invalid")


class TestSavedSchema:
    """Test SavedSchema model."""

    def test_saved_schema_from_dict(self):
        """SavedSchema.from_dict creates a model from API data."""
        schema = SavedSchema.from_dict(
            {
                "name": "invoice-schema",
                "schema_json": {"type": "object", "properties": {}},
            }
        )

        assert schema.name == "invoice-schema"
        assert schema.schema_json == {"type": "object", "properties": {}}

    def test_saved_schema_from_dict_requires_schema_json(self):
        """SavedSchema.from_dict rejects responses without schema_json."""
        with pytest.raises(KeyError, match="schema_json"):
            SavedSchema.from_dict({"name": "invoice-schema"})

    def test_build_api_schema_returns_copy(self):
        """build_api_schema returns a copy safe to mutate downstream."""
        schema = SavedSchema(
            name="invoice-schema",
            schema_json={"type": "object", "properties": {"total": {"type": "number"}}},
        )

        result = schema.build_api_schema()
        result["properties"]["total"]["type"] = "string"

        assert schema.schema_json["properties"]["total"]["type"] == "number"


class TestSavedSchemaList:
    """Test SavedSchemaList model."""

    def test_saved_schema_list_from_dict(self):
        """SavedSchemaList.from_dict creates the list model from API data."""
        schema_list = SavedSchemaList.from_dict(
            {
                "detail": "Retrieved 2 saved schemas.",
                "count": 2,
                "schemas": [
                    {"name": "invoice", "schema_json": {"type": "object"}},
                    {"name": "receipt", "schema_json": {"type": "array"}},
                ],
            }
        )

        assert schema_list.count == 2
        assert schema_list.detail == "Retrieved 2 saved schemas."
        assert [schema.name for schema in schema_list.schemas] == [
            "invoice",
            "receipt",
        ]


class TestFileClass:
    """Test FileClass model."""

    def test_file_class_from_dict(self):
        """FileClass.from_dict creates a model from API data."""
        file_class = FileClass.from_dict(
            {
                "label": "invoice",
                "description": "An invoice document",
                "create_time": "2024-01-01T12:00:00Z",
            }
        )

        assert file_class.label == "invoice"
        assert file_class.description == "An invoice document"
        assert file_class.create_time is not None

    def test_to_api_dict(self):
        """to_api_dict returns the classification payload shape."""
        file_class = FileClass(label="receipt", description="A receipt")

        assert file_class.to_api_dict() == {
            "label": "receipt",
            "description": "A receipt",
        }


class TestFileClassList:
    """Test FileClassList model."""

    def test_file_class_list_from_dict(self):
        """FileClassList.from_dict creates the list model from API data."""
        class_list = FileClassList.from_dict(
            {
                "detail": "Retrieved 1 user file classes.",
                "count": 1,
                "classes": [
                    {"label": "invoice", "description": "An invoice document"},
                ],
            }
        )

        assert class_list.count == 1
        assert class_list.classes[0].label == "invoice"


class TestClassificationJob:
    """Test ClassificationJob model."""

    def test_classification_job_properties(self):
        """Classification job status properties work correctly."""
        completed = ClassificationJob(id="cls_1", processing_status="completed")
        failed = ClassificationJob(id="cls_2", processing_status="failed")
        processing = ClassificationJob(id="cls_3", processing_status="processing")

        assert completed.is_completed is True
        assert failed.is_failed is True
        assert processing.is_processing is True

    def test_classification_job_from_dict(self):
        """ClassificationJob.from_dict creates a model from API data."""
        job = ClassificationJob.from_dict(
            {
                "job_id": "cls_123",
                "processing_status": "completed",
                "document_class": "invoice",
                "nickname": "March docs",
                "is_internal": False,
                "credits_cost": 1.5,
            }
        )

        assert job.id == "cls_123"
        assert job.document_class == "invoice"
        assert job.nickname == "March docs"
        assert job.credits_cost == 1.5


class TestClassificationJobList:
    """Test ClassificationJobList model."""

    def test_classification_job_list_from_dict(self):
        """ClassificationJobList.from_dict creates the list model from API data."""
        job_list = ClassificationJobList.from_dict(
            {
                "detail": "Retrieved 1 classification jobs.",
                "count": 1,
                "classification_jobs": [
                    {"id": "cls_123", "processing_status": "completed"},
                ],
            }
        )

        assert job_list.count == 1
        assert job_list.jobs[0].id == "cls_123"
