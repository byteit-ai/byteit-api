"""ByteIT API client."""

import json
import time
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

import requests

from ._http import (
    CLASSIFICATION_JOBS_PATH,
    CUSTOM_JOBS_PATH,
    EXTRACT_JOBS_PATH,
    PARSE_JOBS_PATH,
    build_file_class_collection_path,
    build_job_collection_path,
    build_job_resource_path,
    build_job_result_path,
    build_job_status_path,
    build_schema_collection_path,
    build_schema_resource_path,
    build_user_file_class_collection_path,
    build_user_file_class_resource_path,
    build_url,
    extract_job_data,
    handle_response,
    is_duplicate_saved_schema_error,
)
from ._polling import (
    wait_for_classification_job_completion,
    wait_for_completion,
    wait_for_custom_job_completion,
    wait_for_extract_completion,
)
from ._rate_limit import RateLimitedSubmitter
from .connectors import (
    InputConnector,
    LocalFileInputConnector,
    LocalFileOutputConnector,
    OutputConnector,
)
from .exceptions import (
    APIKeyError,
    JobProcessingError,
    ValidationError,
)
from .models.ClassificationJob import ClassificationJob
from .models.ClassificationJobList import ClassificationJobList
from .models.CustomJob import CustomJob
from .models.CustomJobList import CustomJobList
from .models.DocumentType import DocumentType
from .models.ExtractJob import ExtractJob
from .models.ExtractJobList import ExtractJobList
from .models.FileClass import FileClass
from .models.FileClassList import FileClassList
from .models.JobList import JobList
from .models.JobStatus import JobStatus
from .models.OutputFormat import OutputFormat
from .models.ParseJob import ParseJob
from .models.ProcessingOptions import ProcessingOptions
from .models.SavedSchema import SavedSchema
from .models.SavedSchemaList import SavedSchemaList
from .validations import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILES_PER_REQUEST,
    MAX_TOTAL_REQUEST_BYTES,
)


class ByteITClient:
    """Client for ByteIT document parsing.

    Provides both synchronous and asynchronous document parsing workflows.

    Methods:
        parse(input, ...):                Parse a document and wait for the result.
        parse_async(input, ...):          Submit a document for parsing, return.
        get_parse_job_details(job_id):    Get the full parse-job resource.
        get_job_status(job_id):           Check the lightweight processing status.
        get_parse_job_result(job_id):     Download the result of a completed job.
        get_parse_jobs():                 List all parse jobs for your account.
        get_extract_jobs():               List all extract jobs for your account.
        get_extract_job_details(job_id):  Get the full extract-job resource.
        get_extract_job_result(job_id):   Download the result of a completed extraction.
        save_schema(name, schema):        Save a reusable extraction schema.
        get_saved_schemas():              List saved schemas for your account.
        get_saved_schema(name):           Retrieve one saved schema by name.
        delete_saved_schema(name):        Delete one saved schema by name.
        get_default_file_classes():       List system default classification labels.
        save_file_class(label, desc):     Save a classification label for your account.
        get_saved_file_classes():         List saved classification labels.
        get_saved_file_class(label):      Retrieve one saved classification label.
        update_file_class(label, ...):    Update a saved classification label.
        delete_file_class(label):         Delete a saved classification label.
        classify(input, ...):             Classify a document and wait for the result.
        classify_async(input, ...):       Submit a classification job and return.
        get_classification_jobs():        List classification jobs for your account.
        get_classification_job_details(): Get the full classification-job resource.
        get_classification_job_result():  Download a completed classification result.
        custom_job(input, ...):           Submit documents for a custom job and wait.
        custom_job_async(input, ...):     Submit a custom job and return immediately.
        get_custom_jobs(before=None):     List custom jobs for your account.
        get_custom_job_result(job_id):    Download the result of a completed custom job.

    Examples:
        Synchronous (blocking)::

            client = ByteITClient(api_key="your_key") result =
            client.parse("document.pdf")

        Asynchronous (non-blocking)::

            job = client.parse_async("document.pdf") # ... do other work ...
            status = client.get_job_status(job.id)
            if status.is_completed:
                details = client.get_parse_job_details(job.id)
                result = client.get_parse_job_result(details.id)
    """

    BASE_URL = "https://byteit.ai"
    DEFAULT_TIMEOUT = 60 * 30  # 30 minutes

    def __init__(
        self,
        api_key: str,
        *,
        rate_limit_max_retries: int = 10,
        rate_limit_base_delay: float = 1.0,
        rate_limit_max_delay: float = 60.0,
        batch_request_delay: float = 1.0,
    ):
        """Initialize the ByteIT client.

        Args:
            api_key: Your ByteIT API key
            rate_limit_max_retries: Maximum submission retries after a 429 response.
            rate_limit_base_delay: Initial wait time (seconds) after rate limiting.
            rate_limit_max_delay: Maximum adaptive delay (seconds) between submissions.
            batch_request_delay: Pause (seconds) between consecutive batch requests
                when uploading a folder, to avoid tripping rate limits.

        Raises:
            APIKeyError: If API key is invalid
        """
        if not api_key:
            raise APIKeyError("API key must be a non-empty string")

        self.api_key = api_key
        self._batch_request_delay = batch_request_delay
        self._session = requests.Session()
        self._session.headers.update({"X-API-Key": self.api_key})

        self._rate_limiter = RateLimitedSubmitter(
            session=self._session,
            base_url=self.BASE_URL,
            default_timeout=self.DEFAULT_TIMEOUT,
            rate_limit_max_retries=rate_limit_max_retries,
            rate_limit_base_delay=rate_limit_base_delay,
            rate_limit_max_delay=rate_limit_max_delay,
        )

    # ==================== PUBLIC API ====================

    def parse(
        self,
        input: str | Path | InputConnector,
        processing_options: ProcessingOptions | dict | None = None,
        output: None | str | Path = None,
        output_format: str | OutputFormat | None = None,
    ) -> bytes:
        """Parse a document and wait for the result.

        Submits the document, polls until processing completes, and returns
        the parsed content. For non-blocking usage, see :meth:`parse_async`.

        Args:
            input: File path (str/Path) or InputConnector.
            output: Optional file path to save the result to disk.
            processing_options: ProcessingOptions or dict with keys:
                ``languages`` (list[str]), ``page_range`` (str), and
                ``parse_type`` (str or ParseType).
                ``image_annotations`` (bool), ``force_image_annotations`` (bool),
                ``table_enrichment`` (bool)
            output_format: Optional output format override. When omitted, the
                backend returns the format that was requested when the job was
                created. Supported values are ``OutputFormat.TXT``,
                ``OutputFormat.JSON``, ``OutputFormat.MD``,
                ``OutputFormat.HTML``, and ``OutputFormat.EXCEL``.

        Returns:
            Parsed content as bytes.
            IMPORTANT: If output format is set to EXCEL,
            it returns bytes of a zip file containing the Excel file.

        Example::

            result = client.parse("document.pdf")
            client.parse("doc.pdf", output="result.md")
            client.parse("doc.pdf", output_format=OutputFormat.TXT)
        """
        job, input_connector = self._submit_job(
            input,
            processing_options,
            output=output,
        )
        print(f"Job {job.id} created. Waiting for completion...")
        self._wait_for_completion(job.id, input_connector=input_connector, job=job)

        # Download result
        fmt = (
            self._parse_output_format(output_format)
            if output_format is not None
            else None
        )
        result_bytes = self._download_parse_result(job.id, result_format=fmt)

        # If output is a file path, save it
        if isinstance(output, (str, Path)):
            Path(output).write_bytes(result_bytes)

        return result_bytes

    def parse_async(
        self,
        input: str | Path | InputConnector | list[str | Path],
        processing_options: ProcessingOptions | dict | None = None,
        queue_for_batch: bool = False,
    ) -> ParseJob | list[ParseJob]:
        """Submit one or many documents for parsing and return immediately.

        Use this for non-blocking workflows. Check progress with
        :meth:`get_job_status`, inspect metadata with :meth:`get_parse_job_details`,
        and retrieve results with :meth:`get_parse_job_result`.

        ``input`` may be:

        * A single file path (str/Path) or an :class:`InputConnector` — returns
          a single :class:`ParseJob`.
        * A ``list[str | Path]```of file paths — every file is uploaded.
          Files are packed into as few requests as the backend allows
          (up to :data:`MAX_FILES_PER_REQUEST` files and
          :data:`MAX_TOTAL_REQUEST_BYTES` per request), and requests are sent
          one after another with a short pause in between and automatic retries
          when rate limited. Returns a ``list[ParseJob]``.

        Args:
            input: File path, folder path, InputConnector, or a list of file
                paths.
            processing_options: ProcessingOptions or dict with keys:
                ``languages`` (list[str]), ``page_range`` (str), and
                ``parse_type`` (str or ParseType).
            queue_for_batch: When ``True``, the job is queued for batch
                processing at a reduced credit cost. Processing is not
                immediate.

        Returns:
            A single :class:`ParseJob` for a file/connector input, or a
            ``list[ParseJob]`` (one per successfully submitted file) for a
            list of file paths.

        Example::

            # Single file
            job = client.parse_async("document.pdf")
            status = client.get_job_status(job.id)

            # Multiple files — the library splits them into batched requests
            jobs = client.parse_async(["./invoice1.pdf", "./invoice2.pdf"])
            for j in jobs:
                print(j.id, j.processing_status)
        """
        if isinstance(input, list):
            return self._submit_file_list(
                [Path(p) if isinstance(p, str) else p for p in input],
                processing_options,
                queue_for_batch=queue_for_batch,
            )

        if self._is_directory_input(input):
            return self._submit_folder_async(
                Path(input),  # type: ignore[arg-type]
                processing_options,
                queue_for_batch=queue_for_batch,
            )

        job, _ = self._submit_job(
            input, processing_options, queue_for_batch=queue_for_batch
        )
        print(f"Job {job.id} submitted.")
        return job

    def get_parse_jobs(self) -> JobList:
        """List all parse jobs for your account.

        Returns:
            JobList response with collection metadata and parse jobs.

        Example::

            job_list = client.get_parse_jobs()
            for job in job_list.jobs:
                print(f"{job.id}: {job.processing_status}")
        """
        return self._list_parse_jobs()

    def get_parse_job_details(self, job_id: str) -> ParseJob:
        """Get the full parse-job resource for a job.

        Args:
            job_id: The job ID.

        Returns:
            ParseJob object with backend detail fields and metadata.

        Example::

            job = client.get_parse_job_details("job_123")
            print(job.result_format)
        """
        return self._get_parse_job_details(job_id)

    def get_job_status(self, job_id: str) -> JobStatus:
        """Check the lightweight processing status of a job.

        Args:
            job_id: The job ID.

        Returns:
            JobStatus object with progress, status, and backend message.

        Example::

            status = client.get_job_status("job_123")
            if status.is_completed:
                result = client.get_parse_job_result("job_123")
        """
        return self._get_job_status(job_id)

    def get_parse_job_result(
        self,
        job_id: str,
        result_format: str | OutputFormat | None = None,
    ) -> bytes:
        """Download the result of a completed parse job.

        Args:
            job_id: The job ID.
            result_format: Optional output format override. When omitted, the
                backend returns the format that was requested when the job was
                created. Supported values are ``OutputFormat.TXT``,
                ``OutputFormat.JSON``, ``OutputFormat.MD``,
                ``OutputFormat.HTML``, and ``OutputFormat.EXCEL``.

        Returns:
            Parsed content as bytes.

        Raises:
            JobProcessingError: If the job has not completed yet.

        Example::

            result = client.get_parse_job_result("job_123")
            result = client.get_parse_job_result(
                "job_123", result_format=OutputFormat.TXT
            )
            with open("output.txt", "wb") as f:
                f.write(result)
        """
        if result_format is None:
            return self._download_parse_result(job_id)

        fmt = self._parse_output_format(result_format)
        return self._download_parse_result(job_id, result_format=fmt)

    # ==================== EXTRACTION PUBLIC API ====================

    def extract(
        self,
        parse_job_id: str,
        schema: type | dict[str, Any] | SavedSchema,
        output: None | str | Path = None,
        extraction_complexity: str = "medium",
    ) -> dict[str, Any]:
        """Run extraction on a completed parse job and wait for the result.

        Submits an extraction job against an existing parse job, polls until
        processing completes, and returns the extracted fields as a dictionary.
        For non-blocking usage, see :meth:`extract_async`.

        Args:
            parse_job_id: ID of a completed
                :class:`~byteit.models.ParseJob.ParseJob` to extract from.
            schema: Extraction schema defining the fields to extract. Accepts
                a subclass of
                :class:`~byteit.models.ExtractionSchema.ExtractionSchema`,
                a raw JSON schema dict, or a
                :class:`~byteit.models.SavedSchema.SavedSchema` instance
                (for example, from :meth:`get_saved_schema`). For saved
                schemas, the ``schema_json`` field is sent to the API via
                :meth:`~byteit.models.SavedSchema.SavedSchema.build_api_schema`.
            output: Optional file path to save the JSON result to disk.
            extraction_complexity: Complexity tier for the extraction.
                One of ``"low"``, ``"medium"``, or ``"high"``.
                Defaults to ``"medium"``.

        Returns:
            Extracted fields as a dictionary matching the provided schema.

        Example::

            from byteit import ExtractionSchema
            from pydantic import Field

            class InvoiceSchema(ExtractionSchema):
                invoice_number: str | None = Field(description="Invoice number.")
                total_amount: str | None = Field(description="Total amount due.")

            result = client.extract(
                parse_job_id, InvoiceSchema, extraction_complexity="medium"
            )
        """
        job = self._create_extract_job(parse_job_id, schema, extraction_complexity)
        print(f"Extraction job {job.id} created. Waiting for completion...")
        self._wait_for_extract_completion(job.id, job)

        result = self._download_extract_result(job.id)

        if isinstance(output, (str, Path)):
            Path(output).write_text(
                json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        return result

    def extract_async(
        self,
        parse_job_id: str,
        schema: type | dict[str, Any] | SavedSchema,
        extraction_complexity: str = "medium",
    ) -> ExtractJob:
        """Submit a structured field extraction job and return immediately.

        Use this for non-blocking workflows. Check progress with
        :meth:`get_job_status`, and retrieve results with
        :meth:`get_extract_job_result`.

        Args:
            parse_job_id: ID of a completed
                :class:`~byteit.models.ParseJob.ParseJob` to extract from.
            schema: Extraction schema defining the fields to extract. Accepts
                a subclass of
                :class:`~byteit.models.ExtractionSchema.ExtractionSchema`,
                a raw JSON schema dict, or a
                :class:`~byteit.models.SavedSchema.SavedSchema` instance
                (for example, from :meth:`get_saved_schema`). For saved
                schemas, the ``schema_json`` field is sent to the API via
                :meth:`~byteit.models.SavedSchema.SavedSchema.build_api_schema`.
            extraction_complexity: Complexity tier for the extraction.
                One of ``"low"``, ``"medium"``, or ``"high"``.
                Defaults to ``"medium"``.

        Returns:
            ExtractJob object with ``id`` and ``processing_status``.

        Example::

            job = client.extract_async(
                parse_job_id, InvoiceSchema, extraction_complexity="high"
            )
            # ... do other work ...
            status = client.get_job_status(job.id)
            if status.is_completed:
                result = client.get_extract_job_result(job.id)
        """
        job = self._create_extract_job(parse_job_id, schema, extraction_complexity)
        print(f"Extraction job {job.id} submitted.")
        return job

    def get_extract_jobs(self) -> ExtractJobList:
        """List all extraction jobs for your account.

        Returns:
            ExtractJobList with collection metadata and extract jobs.

        Example::

            job_list = client.get_extract_jobs()
            for job in job_list.jobs:
                print(f"{job.id}: {job.processing_status}")
        """
        return self._list_extract_jobs()

    def get_extract_job_details(self, job_id: str) -> ExtractJob:
        """Get the full extract-job resource.

        Args:
            job_id: The extraction job ID.

        Returns:
            ExtractJob object with status and metadata.

        Example::

            job = client.get_extract_job_details("job_123")
            print(job.processing_status)
        """
        return self._get_extract_job_details(job_id)

    def get_extract_job_result(self, job_id: str) -> dict[str, Any]:
        """Download the result of a completed extraction job.

        Args:
            job_id: The extraction job ID.

        Returns:
            Extracted fields as a dictionary.

        Raises:
            JobProcessingError: If the job has not completed yet.

        Example::

            result = client.get_extract_job_result("job_123")
        """
        return self._download_extract_result(job_id)

    # ==================== SAVED SCHEMA PUBLIC API ====================

    def save_schema(
        self,
        name: str,
        schema: type | dict[str, Any] | SavedSchema,
    ) -> SavedSchema:
        """Save a reusable extraction schema for the authenticated user.

        Args:
            name: Human-readable schema name.
            schema: A subclass of
                :class:`~byteit.models.ExtractionSchema.ExtractionSchema`,
                a raw JSON schema dict, or a
                :class:`~byteit.models.SavedSchema.SavedSchema` instance.
                The payload persisted as ``schema_json`` is taken from the
                dict directly, from ``build_api_schema()`` on schema classes,
                or from
                :meth:`~byteit.models.SavedSchema.SavedSchema.build_api_schema`
                when re-saving an existing saved schema.

        Returns:
            SavedSchema object with the persisted name and schema payload.

        Example::

            saved_schema = client.save_schema("invoice", InvoiceSchema)
            print(saved_schema.name)
        """
        normalized_name = self._normalize_schema_name(name)
        schema_dict = self._build_schema_dict(schema)

        try:
            return self._create_saved_schema(
                name=normalized_name, schema_json=schema_dict
            )
        except ValidationError as exc:
            if not is_duplicate_saved_schema_error(exc):
                raise

            existing_schema = self._get_saved_schema(normalized_name)
            if existing_schema.schema_json == schema_dict:
                return existing_schema

            raise ValidationError(
                f"Schema '{normalized_name}' already exists with different content. "
                "Load it with get_saved_schema() or delete it before saving a "
                "new definition.",
                exc.status_code,
                exc.response,
            ) from exc

    def get_saved_schemas(self) -> SavedSchemaList:
        """List all saved schemas for the authenticated user.

        Returns:
            SavedSchemaList containing the saved schemas and list metadata.

        Example::

            saved_schemas = client.get_saved_schemas()
            for saved_schema in saved_schemas.schemas:
                print(saved_schema.name)
        """
        return self._list_saved_schemas()

    def get_saved_schema(self, name: str) -> SavedSchema:
        """Retrieve a saved schema by name.

        Args:
            name: Saved schema name.

        Returns:
            SavedSchema object.

        Example::

            saved_schema = client.get_saved_schema("invoice")
            print(saved_schema.schema_json)
        """
        return self._get_saved_schema(name=name)

    def delete_saved_schema(self, name: str) -> bool:
        """Delete a saved schema by name.

        Args:
            name: Saved schema name.

        Returns:
            True when the schema was deleted.

        Example::

            client.delete_saved_schema("invoice")
        """
        return self._delete_saved_schema(name=name)

    # ==================== FILE CLASS PUBLIC API ====================

    def get_default_file_classes(self) -> FileClassList:
        """List the system default classification labels and descriptions.

        These defaults are used when a classification job is created without
        custom classes.

        Returns:
            FileClassList containing the default labels.

        Example::

            defaults = client.get_default_file_classes()
            for file_class in defaults.classes:
                print(f"{file_class.label}: {file_class.description}")
        """
        return self._list_default_file_classes()

    def save_file_class(self, label: str, description: str) -> FileClass:
        """Save a classification label for the authenticated user.

        Args:
            label: Unique class label for your account.
            description: Description used by the classifier for this label.

        Returns:
            FileClass object with the persisted label and description.

        Example::

            file_class = client.save_file_class(
                "purchase_order",
                "A purchase order requesting goods or services.",
            )
            print(file_class.label)
        """
        return self._create_user_file_class(label=label, description=description)

    def get_saved_file_classes(self) -> FileClassList:
        """List all classification labels saved by the authenticated user.

        Returns:
            FileClassList containing the saved labels and list metadata.

        Example::

            saved = client.get_saved_file_classes()
            for file_class in saved.classes:
                print(file_class.label)
        """
        return self._list_user_file_classes()

    def get_saved_file_class(self, label: str) -> FileClass:
        """Retrieve a saved classification label by label key.

        Args:
            label: Saved file-class label.

        Returns:
            FileClass object.

        Example::

            file_class = client.get_saved_file_class("purchase_order")
            print(file_class.description)
        """
        return self._get_user_file_class(label=label)

    def update_file_class(
        self,
        label: str,
        *,
        new_label: str | None = None,
        description: str | None = None,
    ) -> FileClass:
        """Update a saved classification label and/or description.

        Args:
            label: Current file-class label to update.
            new_label: Optional replacement label.
            description: Optional replacement description.

        Returns:
            Updated FileClass object.

        Example::

            updated = client.update_file_class(
                "purchase_order",
                description="Updated purchase-order description.",
            )
        """
        return self._update_user_file_class(
            label=label,
            new_label=new_label,
            description=description,
        )

    def delete_file_class(self, label: str) -> bool:
        """Delete a saved classification label by label key.

        Args:
            label: Saved file-class label.

        Returns:
            True when the file class was deleted.

        Example::

            client.delete_file_class("purchase_order")
        """
        return self._delete_user_file_class(label=label)

    # ==================== CLASSIFICATION JOB PUBLIC API ====================

    def classify(
        self,
        input: str | Path | InputConnector,
        classes: list[FileClass | dict[str, str]] | None = None,
        nickname: str | None = None,
        output: None | str | Path = None,
    ) -> dict[str, Any]:
        """Classify a document and wait for the result.

        Submits the document, polls until processing completes, and returns
        the classification result. When ``classes`` is omitted, system default
        labels are used. When provided, only the given classes are used for
        that job.

        Args:
            input: File path (str/Path) or InputConnector.
            classes: Optional list of :class:`~byteit.models.FileClass.FileClass`
                instances or ``{label, description}`` dicts. Omit to use
                system defaults.
            nickname: Optional label for easier job identification.
            output: Optional file path to save the JSON result to disk.

        Returns:
            Classification result dictionary with ``document_class`` and
            ``classification_response``.

        Example::

            result = client.classify("document.pdf")
            print(result["document_class"])

            result = client.classify(
                "document.pdf",
                classes=[
                    {"label": "invoice", "description": "An invoice document"},
                    {"label": "receipt", "description": "A payment receipt"},
                ],
            )
        """
        job = self._create_classification_job(input, classes, nickname)
        print(f"Classification job {job.id} created. Waiting for completion...")
        self._wait_for_classification_job_completion(job.id, job)

        result = self._download_classification_result(job.id)

        if isinstance(output, (str, Path)):
            Path(output).write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return result

    def classify_async(
        self,
        input: str | Path | InputConnector,
        classes: list[FileClass | dict[str, str]] | None = None,
        nickname: str | None = None,
    ) -> ClassificationJob:
        """Submit a classification job and return immediately.

        Use this for non-blocking workflows. Check progress with
        :meth:`get_job_status`, and retrieve results with
        :meth:`get_classification_job_result`.

        Args:
            input: File path (str/Path) or InputConnector.
            classes: Optional list of :class:`~byteit.models.FileClass.FileClass`
                instances or ``{label, description}`` dicts. Omit to use
                system defaults.
            nickname: Optional label for easier job identification.

        Returns:
            ClassificationJob object with ``id`` and ``processing_status``.

        Example::

            job = client.classify_async("document.pdf")
            status = client.get_job_status(job.id)
            if status.is_completed:
                result = client.get_classification_job_result(job.id)
        """
        job = self._create_classification_job(input, classes, nickname)
        print(f"Classification job {job.id} submitted.")
        return job

    def get_classification_jobs(self) -> ClassificationJobList:
        """List classification jobs for your account.

        Returns:
            ClassificationJobList with collection metadata and jobs.

        Example::

            job_list = client.get_classification_jobs()
            for job in job_list.jobs:
                print(f"{job.id}: {job.processing_status}")
        """
        return self._list_classification_jobs()

    def get_classification_job_details(self, job_id: str) -> ClassificationJob:
        """Get the full classification-job resource.

        Args:
            job_id: The classification job ID.

        Returns:
            ClassificationJob object with status and metadata.

        Example::

            job = client.get_classification_job_details("job_123")
            print(job.document_class)
        """
        return self._get_classification_job_details(job_id)

    def get_classification_job_result(self, job_id: str) -> dict[str, Any]:
        """Download the result of a completed classification job.

        Args:
            job_id: The classification job ID.

        Returns:
            Classification result dictionary with ``document_class`` and
            ``classification_response``.

        Raises:
            JobProcessingError: If the job has not completed yet.

        Example::

            result = client.get_classification_job_result("job_123")
            print(result["document_class"])
        """
        return self._download_classification_result(job_id)

    # ==================== CUSTOM JOB PUBLIC API ====================

    def custom_job(
        self,
        input: str | Path | InputConnector | list[str | Path | InputConnector],
        schema: type | dict[str, Any] | None = None,
        user_prompt: str | None = None,
        nickname: str | None = None,
        output: None | str | Path = None,
    ) -> dict[str, Any] | str:
        """Submit documents for a custom job and wait for the result.

        Uploads one or more documents with an optional schema and user prompt,
        polls until processing completes, and returns the result.
        For non-blocking usage, see :meth:`custom_job_async`.

        When a schema is provided the result is returned as a dictionary.
        Without a schema the result is returned as a string (for example
        markdown or plain text produced by the model).

        Args:
            input: Single file path (str/Path), InputConnector, or a list of
                those values for multi-document jobs.
            schema: Optional subclass of
                :class:`~byteit.models.ExtractionSchema.ExtractionSchema`
                or a raw JSON schema dict defining fields to extract.
            user_prompt: Optional prompt appended to the custom job request.
            nickname: Optional label for easier job identification.
            output: Optional file path to save the result to disk.

        Returns:
            Parsed JSON as a dictionary when the result is JSON, otherwise
            the raw result text.

        Example::

            result = client.custom_job(
                ["invoice1.pdf"],
                schema={"invoice_number": "string"},
                user_prompt="Focus on the billing section.",
                nickname="March invoices",
            )
        """
        job = self._create_custom_job(input, schema, user_prompt, nickname)
        print(f"Custom job {job.id} created. Waiting for completion...")
        self._wait_for_custom_job_completion(job.id, job)

        result_bytes = self._download_custom_job_result(job.id)
        result = self._parse_custom_job_result(result_bytes)

        if isinstance(output, (str, Path)):
            if isinstance(result, dict):
                Path(output).write_text(
                    json.dumps(result, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            else:
                Path(output).write_text(result, encoding="utf-8")

        return result

    def custom_job_async(
        self,
        input: str | Path | InputConnector | list[str | Path | InputConnector],
        schema: type | dict[str, Any] | None = None,
        user_prompt: str | None = None,
        nickname: str | None = None,
    ) -> CustomJob:
        """Submit a custom job and return immediately.

        Use this for non-blocking workflows. Check progress with
        :meth:`get_job_status`, and retrieve results with
        :meth:`get_custom_job_result`.

        Args:
            input: Single file path (str/Path), InputConnector, or a list of
                those values for multi-document jobs.
            schema: Optional subclass of
                :class:`~byteit.models.ExtractionSchema.ExtractionSchema`
                or a raw JSON schema dict defining fields to extract.
            user_prompt: Optional prompt appended to the custom job request.
            nickname: Optional label for easier job identification.

        Returns:
            CustomJob object with ``id`` and ``processing_status``.

        Example::

            job = client.custom_job_async(
                "document.pdf",
                schema=InvoiceSchema,
                user_prompt="Extract only the totals.",
            )
            status = client.get_job_status(job.id)
            if status.is_completed:
                result = client.get_custom_job_result(job.id)
        """
        job = self._create_custom_job(input, schema, user_prompt, nickname)
        print(f"Custom job {job.id} submitted.")
        return job

    def get_custom_jobs(
        self,
        before: str | datetime | None = None,
    ) -> CustomJobList:
        """List custom jobs for your account.

        Args:
            before: Optional ISO 8601 datetime cursor for pagination. Returns
                custom jobs created before this time.

        Returns:
            CustomJobList with collection metadata and custom jobs.

        Example::

            job_list = client.get_custom_jobs()
            for job in job_list.jobs:
                print(f"{job.id}: {job.processing_status}")
        """
        return self._list_custom_jobs(before=before)

    def get_custom_job_result(self, job_id: str) -> dict[str, Any] | str:
        """Download the result of a completed custom job.

        The result can only be retrieved once within 30 seconds of completion.

        Args:
            job_id: The custom job ID.

        Returns:
            Parsed JSON as a dictionary when the result is JSON, otherwise
            the raw result text.

        Raises:
            JobProcessingError: If the job has not completed yet.

        Example::

            result = client.get_custom_job_result("job_123")
        """
        return self._parse_custom_job_result(self._download_custom_job_result(job_id))

    # ==================== JOB SUBMISSION ====================

    def _submit_job(
        self,
        input: str | Path | InputConnector,
        processing_options: ProcessingOptions | dict | None = None,
        output: None | str | Path = None,
        queue_for_batch: bool = False,
    ) -> tuple[ParseJob, InputConnector]:
        """Validate inputs, build connectors, and create a job.

        Shared by :meth:`parse` and :meth:`parse_async`.
        """
        if isinstance(processing_options, dict):
            processing_options = ProcessingOptions.from_dict(processing_options)

        input_connector = self._to_input_connector(input)
        output_connector = self._to_output_connector(output)

        job = self._create_job(
            input_connector=input_connector,
            output_connector=output_connector,
            processing_options=processing_options,
            queue_for_batch=queue_for_batch,
        )
        return job, input_connector

    # ==================== FOLDER (MULTI-FILE) SUBMISSION ====================

    @staticmethod
    def _is_directory_input(input: str | Path | InputConnector) -> bool:
        """Return True when the input refers to an existing folder on disk."""
        if isinstance(input, (str, Path)):
            return Path(input).is_dir()
        return False

    def _submit_file_list(
        self,
        files: list[Path],
        processing_options: ProcessingOptions | dict | None,
        queue_for_batch: bool,
        result_format: OutputFormat = OutputFormat.JSON,
    ) -> list[ParseJob]:
        """Submit a list of file paths as batched parse jobs."""
        if isinstance(processing_options, dict):
            processing_options = ProcessingOptions.from_dict(processing_options)

        batches = self._batch_files_by_limits(files)
        data = self._build_localfile_job_data(
            processing_options=processing_options,
            result_format=result_format,
            queue_for_batch=queue_for_batch,
        )

        print(f"Submitting {len(files)} file(s) in {len(batches)} request(s)...")

        created_jobs: list[ParseJob] = []
        failed_files: list[dict[str, Any]] = []

        for index, batch in enumerate(batches, start=1):
            if index > 1 and self._batch_request_delay > 0:
                time.sleep(self._batch_request_delay)

            response = self._rate_limiter.submit_multi_file_batch(batch, data)
            jobs, failures = self._parse_multi_file_response(response)
            created_jobs.extend(jobs)
            failed_files.extend(failures)

            summary = f"  Request {index}/{len(batches)}: {len(jobs)} job(s) created"
            if failures:
                summary += f", {len(failures)} failed"
            print(summary)

        if failed_files:
            print(f"{len(failed_files)} file(s) failed to upload:")
            for failure in failed_files:
                print(
                    f"  - {failure.get('file_name', 'unknown')}: "
                    f"{failure.get('error', 'unknown error')}"
                )

        print(f"Submitted {len(created_jobs)} job(s).")
        return created_jobs

    def _submit_folder_async(
        self,
        folder: Path,
        processing_options: ProcessingOptions | dict | None,
        *,
        queue_for_batch: bool,
        result_format: OutputFormat = OutputFormat.JSON,
    ) -> list[ParseJob]:
        """Upload every supported file in a folder as batched parse jobs."""
        files = self._collect_folder_files(folder)
        if not files:
            raise ValidationError(f"No supported files found in folder: {folder}")

        print(f"Found {len(files)} supported file(s) in '{folder}'.")

        return self._submit_file_list(
            files,
            processing_options,
            queue_for_batch=queue_for_batch,
            result_format=result_format,
        )

    @staticmethod
    def _collect_folder_files(folder: Path) -> list[Path]:
        """Collect uploadable files from a folder, skipping unsupported ones."""
        collected: list[Path] = []
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue

            if not DocumentType.is_supported_extension(path.suffix):
                print(f"Skipping unsupported file type: {path.name}")
                continue

            size = path.stat().st_size
            if size == 0:
                print(f"Skipping empty file: {path.name}")
                continue
            if size > MAX_FILE_SIZE_BYTES:
                limit_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
                print(
                    f"Skipping '{path.name}': exceeds the per-file limit of {limit_mb} MB"
                )
                continue

            collected.append(path)

        return collected

    @staticmethod
    def _batch_files_by_limits(files: list[Path]) -> list[list[Path]]:
        """Greedily pack files into batches within the per-request limits."""
        batches: list[list[Path]] = []
        current: list[Path] = []
        current_size = 0

        for path in files:
            size = path.stat().st_size
            too_many = len(current) >= MAX_FILES_PER_REQUEST
            too_large = bool(current) and (current_size + size > MAX_TOTAL_REQUEST_BYTES)
            if too_many or too_large:
                batches.append(current)
                current = []
                current_size = 0

            current.append(path)
            current_size += size

        if current:
            batches.append(current)

        return batches

    def _build_localfile_job_data(
        self,
        *,
        processing_options: ProcessingOptions | None,
        result_format: OutputFormat,
        queue_for_batch: bool,
    ) -> dict[str, Any]:
        """Build the multipart form fields shared by every folder batch."""
        output_connector = LocalFileOutputConnector()
        output_config = output_connector.to_dict()

        data: dict[str, Any] = {
            "output_format": result_format.value,
            "processing_options": json.dumps(
                processing_options.to_dict() if processing_options else {}
            ),
            "input_connector": "localfile",
            "output_connector": output_config.get("type", ""),
            "output_connection_data": (
                json.dumps(output_config) if output_config.get("type") else "{}"
            ),
        }
        if queue_for_batch:
            data["queue_for_batch"] = "true"
        return data

    @staticmethod
    def _parse_multi_file_response(
        response: dict[str, Any],
    ) -> tuple[list[ParseJob], list[dict[str, Any]]]:
        """Split a multi-file create response into jobs and per-file failures."""
        raw_jobs = response.get("parse_jobs") or []
        jobs = [ParseJob.from_dict(item) for item in raw_jobs if isinstance(item, dict)]
        failures = [
            f for f in (response.get("failed_files") or []) if isinstance(f, dict)
        ]
        return jobs, failures

    # ==================== EXTRACTION INTERNAL METHODS ====================

    def _create_extract_job(
        self,
        parse_job_id: str,
        schema: type | dict[str, Any] | SavedSchema,
        extraction_complexity: str = "medium",
    ) -> ExtractJob:
        """Submit a new extraction job for an existing parse job."""
        schema_dict = self._build_schema_dict(schema)
        response = self._request(
            "POST",
            build_job_collection_path(EXTRACT_JOBS_PATH),
            json={
                "parse_job_id": parse_job_id,
                "schema": schema_dict,
                "extraction_complexity": extraction_complexity,
            },
        )
        job_data = extract_job_data(response, primary_key="extract_job")
        return ExtractJob.from_dict(job_data)

    def _list_extract_jobs(self) -> ExtractJobList:
        """List all extract jobs."""
        response = self._request("GET", build_job_collection_path(EXTRACT_JOBS_PATH))
        return ExtractJobList.from_dict(response)

    def _get_extract_job_details(self, job_id: str) -> ExtractJob:
        """Get current extract-job details."""
        response = self._request(
            "GET", build_job_resource_path(job_id, EXTRACT_JOBS_PATH)
        )
        job_data = extract_job_data(response, primary_key="extract_job")
        return ExtractJob.from_dict(job_data)

    def _download_extract_result(self, job_id: str) -> dict[str, Any]:
        """Download the JSON result of a completed extraction job."""
        data = self._request("GET", build_job_result_path(job_id, EXTRACT_JOBS_PATH))
        data = data if isinstance(data, dict) else {}
        if not data.get("ready", True):
            status = data.get("processing_status", "unknown")
            raise JobProcessingError(f"Result not available. Job status: {status}")

        result = data.get("result", data)
        if not isinstance(result, dict):
            return data
        return result

    def _build_schema_dict(
        self,
        schema: type | dict[str, Any] | SavedSchema,
    ) -> dict[str, Any]:
        """Convert a schema input to a JSON schema payload for the API.

        Accepts a raw dict (returned as-is), an
        :class:`~byteit.models.ExtractionSchema.ExtractionSchema` subclass,
        a plain Pydantic model, or a
        :class:`~byteit.models.SavedSchema.SavedSchema` instance. Saved
        schemas and ExtractionSchema subclasses expose ``build_api_schema()``;
        for saved schemas this returns a copy of ``schema_json``.
        """
        if isinstance(schema, dict):
            return schema

        # Duck-type check: ExtractionSchema subclass (avoids hard pydantic import)
        build_fn = getattr(schema, "build_api_schema", None)
        if callable(build_fn):
            return build_fn()

        # Fall back: plain Pydantic BaseModel class
        json_schema_fn = getattr(schema, "model_json_schema", None)
        if callable(json_schema_fn):
            return json_schema_fn()

        raise ValidationError(
            "schema must be a dict or an object exposing build_api_schema()."
        )

    def _create_saved_schema(
        self,
        name: str,
        schema_json: dict[str, Any],
    ) -> SavedSchema:
        """Persist a pre-built saved schema for the authenticated user."""
        response = self._request(
            "POST",
            build_schema_collection_path(),
            json={"name": name, "schema_json": schema_json},
        )
        return SavedSchema.from_dict(response)

    def _list_saved_schemas(self) -> SavedSchemaList:
        """List all saved schemas for the authenticated user."""
        response = self._request("GET", build_schema_collection_path())
        return SavedSchemaList.from_dict(response)

    def _get_saved_schema(self, name: str) -> SavedSchema:
        """Retrieve a saved schema by name."""
        response = self._request("GET", build_schema_resource_path(name))
        return SavedSchema.from_dict(response)

    def _delete_saved_schema(self, name: str) -> bool:
        """Delete a saved schema by name."""
        self._request("DELETE", build_schema_resource_path(name))
        return True

    # ==================== FILE CLASS INTERNAL METHODS ====================

    def _list_default_file_classes(self) -> FileClassList:
        """List system default classification labels."""
        response = self._request("GET", build_file_class_collection_path())
        return FileClassList.from_dict(response)

    def _create_user_file_class(self, label: str, description: str) -> FileClass:
        """Persist a user-owned classification label."""
        normalized_label = self._normalize_file_class_label(label)
        normalized_description = self._normalize_file_class_description(description)
        response = self._request(
            "POST",
            build_user_file_class_collection_path(),
            json={
                "label": normalized_label,
                "description": normalized_description,
            },
        )
        return FileClass.from_dict(response)

    def _list_user_file_classes(self) -> FileClassList:
        """List all user-owned classification labels."""
        response = self._request("GET", build_user_file_class_collection_path())
        return FileClassList.from_dict(response)

    def _get_user_file_class(self, label: str) -> FileClass:
        """Retrieve a user-owned classification label by key."""
        response = self._request("GET", build_user_file_class_resource_path(label))
        return FileClass.from_dict(response)

    def _update_user_file_class(
        self,
        label: str,
        new_label: str | None = None,
        description: str | None = None,
    ) -> FileClass:
        """Update a user-owned classification label and/or description."""
        payload: dict[str, str] = {}
        if new_label is not None:
            payload["label"] = self._normalize_file_class_label(new_label)
        if description is not None:
            payload["description"] = self._normalize_file_class_description(
                description
            )

        if not payload:
            raise ValidationError(
                "Provide new_label and/or description to update a file class."
            )

        response = self._request(
            "PUT",
            build_user_file_class_resource_path(label),
            json=payload,
        )
        return FileClass.from_dict(response)

    def _delete_user_file_class(self, label: str) -> bool:
        """Delete a user-owned classification label by key."""
        self._request("DELETE", build_user_file_class_resource_path(label))
        return True

    def _normalize_file_class_label(self, label: str) -> str:
        """Normalize a file-class label before sending it to the API."""
        if not isinstance(label, str):
            raise ValidationError("label must be a non-empty string")

        normalized_label = label.strip()
        if not normalized_label:
            raise ValidationError("label must be a non-empty string")

        return normalized_label

    def _normalize_file_class_description(self, description: str) -> str:
        """Normalize a file-class description before sending it to the API."""
        if not isinstance(description, str):
            raise ValidationError("description must be a non-empty string")

        normalized_description = description.strip()
        if not normalized_description:
            raise ValidationError("description must be a non-empty string")

        return normalized_description

    def _build_classification_classes_payload(
        self,
        classes: list[FileClass | dict[str, str]] | None,
    ) -> list[dict[str, str]] | None:
        """Normalize optional classification class inputs for the API."""
        if classes is None:
            return None

        if not isinstance(classes, list):
            raise ValidationError("classes must be a list of FileClass or dict values.")

        if not classes:
            raise ValidationError("classes must contain at least one class.")

        normalized: list[dict[str, str]] = []
        seen_labels: set[str] = set()
        for entry in classes:
            if isinstance(entry, FileClass):
                label = self._normalize_file_class_label(entry.label)
                description = self._normalize_file_class_description(entry.description)
            elif isinstance(entry, dict):
                raw_label = entry.get("label")
                raw_description = entry.get("description")
                if not isinstance(raw_label, str) or not isinstance(
                    raw_description, str
                ):
                    raise ValidationError(
                        "Each class dict requires string label and description."
                    )
                label = self._normalize_file_class_label(raw_label)
                description = self._normalize_file_class_description(raw_description)
            else:
                raise ValidationError(
                    "Each class must be a FileClass or a dict with label and description."
                )

            if label in seen_labels:
                raise ValidationError(f"Duplicate class label '{label}'.")
            seen_labels.add(label)
            normalized.append({"label": label, "description": description})

        return normalized

    # ==================== CLASSIFICATION JOB INTERNAL METHODS ====================

    def _create_classification_job(
        self,
        input: str | Path | InputConnector,
        classes: list[FileClass | dict[str, str]] | None = None,
        nickname: str | None = None,
    ) -> ClassificationJob:
        """Submit a new classification job with an uploaded file."""
        input_connector = self._to_input_connector(input)
        connector_type = (
            input_connector.to_dict().get("type", "localfile").strip().lower()
        )
        if connector_type != "localfile":
            raise ValidationError(
                "Classification jobs currently only support local file uploads."
            )

        data: dict[str, Any] = {}
        classes_payload = self._build_classification_classes_payload(classes)
        if classes_payload is not None:
            data["classes"] = json.dumps(classes_payload)
        if nickname:
            data["nickname"] = nickname

        filename, file_obj = input_connector.get_file_data()
        try:
            response = self._request(
                "POST",
                build_job_collection_path(CLASSIFICATION_JOBS_PATH),
                files={"file": (filename, file_obj)},
                data=data,
            )
        finally:
            if file_obj and hasattr(file_obj, "close") and not file_obj.closed:
                file_obj.close()

        job_data = extract_job_data(response, primary_key="classification_job")
        return ClassificationJob.from_dict(job_data)

    def _list_classification_jobs(self) -> ClassificationJobList:
        """List classification jobs for the authenticated user."""
        response = self._request(
            "GET",
            build_job_collection_path(CLASSIFICATION_JOBS_PATH),
        )
        return ClassificationJobList.from_dict(response)

    def _get_classification_job_details(self, job_id: str) -> ClassificationJob:
        """Get current classification-job details."""
        response = self._request(
            "GET",
            build_job_resource_path(job_id, CLASSIFICATION_JOBS_PATH),
        )
        job_data = extract_job_data(response, primary_key="classification_job")
        return ClassificationJob.from_dict(job_data)

    def _download_classification_result(self, job_id: str) -> dict[str, Any]:
        """Download the JSON result of a completed classification job."""
        data = self._request(
            "GET",
            build_job_result_path(job_id, CLASSIFICATION_JOBS_PATH),
        )
        data = data if isinstance(data, dict) else {}
        if not data.get("ready", True):
            status = data.get("processing_status", "unknown")
            raise JobProcessingError(f"Result not available. Job status: {status}")

        return {
            "job_id": data.get("job_id", job_id),
            "processing_status": data.get("processing_status"),
            "document_class": data.get("document_class"),
            "classification_response": data.get("classification_response"),
        }

    # ==================== CUSTOM JOB INTERNAL METHODS ====================

    def _normalize_custom_job_inputs(
        self,
        input: str | Path | InputConnector | list[str | Path | InputConnector],
    ) -> list[str | Path | InputConnector]:
        """Normalize custom-job file inputs to a non-empty list."""
        if isinstance(input, (str, Path, InputConnector)):
            return [input]

        if isinstance(input, list):
            if not input:
                raise ValidationError("At least one input file is required.")
            return input

        raise ValidationError(
            f"Unsupported custom job input type: {type(input).__name__}"
        )

    def _create_custom_job(
        self,
        input: str | Path | InputConnector | list[str | Path | InputConnector],
        schema: type | dict[str, Any] | None = None,
        user_prompt: str | None = None,
        nickname: str | None = None,
    ) -> CustomJob:
        """Submit a new custom job with one or more uploaded files."""
        inputs = self._normalize_custom_job_inputs(input)
        multipart_files: list[tuple[str, tuple[str, Any]]] = []
        file_handles: list[Any] = []
        data: dict[str, Any] = {}

        if schema is not None:
            data["schema"] = json.dumps(self._build_schema_dict(schema))
        if user_prompt:
            data["user_prompt"] = user_prompt
        if nickname:
            data["nickname"] = nickname

        try:
            for file_input in inputs:
                input_connector = self._to_input_connector(file_input)
                connector_type = (
                    input_connector.to_dict().get("type", "localfile").strip().lower()
                )
                if connector_type != "localfile":
                    raise ValidationError(
                        "Custom jobs currently only support local file uploads."
                    )

                filename, file_obj = input_connector.get_file_data()
                file_handles.append(file_obj)
                multipart_files.append(("files", (filename, file_obj)))

            response = self._request(
                "POST",
                build_job_collection_path(CUSTOM_JOBS_PATH),
                files=multipart_files,
                data=data,
            )
        finally:
            for file_obj in file_handles:
                if file_obj and hasattr(file_obj, "close") and not file_obj.closed:
                    file_obj.close()

        job_data = extract_job_data(response, primary_key="custom_job")
        return CustomJob.from_dict(job_data)

    def _list_custom_jobs(
        self,
        before: str | datetime | None = None,
    ) -> CustomJobList:
        """List custom jobs with optional cursor pagination."""
        params: dict[str, str] = {}
        if before is not None:
            if isinstance(before, datetime):
                params["before"] = before.isoformat()
            else:
                params["before"] = before

        response = self._request(
            "GET",
            build_job_collection_path(CUSTOM_JOBS_PATH),
            params=params or None,
        )
        return CustomJobList.from_dict(response)

    def _download_custom_job_result(self, job_id: str) -> bytes:
        """Download the raw result bytes of a completed custom job."""
        url = build_url(self.BASE_URL, build_job_result_path(job_id, CUSTOM_JOBS_PATH))
        response = self._session.get(url, timeout=self.DEFAULT_TIMEOUT)
        if response.status_code not in (200, 201):
            handle_response(response)

        content_disposition = response.headers.get("Content-Disposition", "")
        content_type = response.headers.get("Content-Type", "")

        if "attachment" in content_disposition:
            if not response.content:
                raise JobProcessingError("Custom job result is empty")
            return response.content

        if "application/json" in content_type:
            data = handle_response(response)
            if not data.get("ready", True):
                status = data.get("processing_status", "unknown")
                raise JobProcessingError(f"Result not available. Job status: {status}")
            raise JobProcessingError("Job ready but no result file returned")

        if not response.content:
            raise JobProcessingError("Custom job result is empty")
        return response.content

    @staticmethod
    def _parse_custom_job_result(content: bytes) -> dict[str, Any] | str:
        """Parse custom job result bytes into a dict or raw text."""
        if not content:
            raise JobProcessingError("Custom job result is empty")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content.decode("utf-8")

        if isinstance(parsed, dict):
            return parsed
        return content.decode("utf-8")

    # ==================== CONNECTOR CONVERTERS ====================

    def _to_input_connector(self, input: str | Path | InputConnector) -> InputConnector:
        """Convert various input types to InputConnector."""
        # Already a connector (checks for InputConnector or its subclasses)
        if isinstance(input, InputConnector):
            return input

        # String or Path - local file
        if not isinstance(input, (str, Path)):
            raise ValidationError(f"Unsupported input type: {type(input).__name__}")

        return LocalFileInputConnector(file_path=str(input))

    def _to_output_connector(self, output: None | str | Path):  # noqa: ARG002
        """Convert output specification to OutputConnector."""
        # Always use ByteIT storage (simplest approach)
        # If output is a file path, we download and save after completion
        return LocalFileOutputConnector()

    def _parse_output_format(self, result_format: str | OutputFormat) -> OutputFormat:
        """Parse a public result format input into an OutputFormat."""
        if isinstance(result_format, OutputFormat):
            return result_format

        if isinstance(result_format, str):
            normalized_result_format = result_format.strip().lower()
            for output_format in OutputFormat:
                if normalized_result_format in (
                    output_format.name.lower(),
                    output_format.value.lower(),
                ):
                    return output_format

        supported_tokens = []
        for output_format in OutputFormat:
            for token in (output_format.name.lower(), output_format.value.lower()):
                if token not in supported_tokens:
                    supported_tokens.append(token)
        supported_formats = ", ".join(supported_tokens)
        raise ValidationError(
            f"result_format must be an OutputFormat or one of: {supported_formats}"
        )

    # ==================== INTERNAL METHODS ====================

    def _create_job(
        self,
        input_connector: InputConnector,
        output_connector: OutputConnector,
        processing_options: ProcessingOptions | None = None,
        queue_for_batch: bool = False,
    ) -> ParseJob:
        """Create a processing job."""
        connector_type = (
            input_connector.to_dict().get("type", "localfile").strip().lower()
        )

        # Build base request data
        data: dict[str, Any] = {
            "processing_options": json.dumps(
                processing_options.to_dict() if processing_options else {}
            ),
            "input_connector": connector_type,
        }

        # Add output connector config
        output_config = output_connector.to_dict()
        data["output_connector"] = output_config.get("type", "")
        data["output_connection_data"] = (
            json.dumps(output_config) if output_config.get("type") else "{}"
        )

        if queue_for_batch:
            data["queue_for_batch"] = "true"

        # Prepare input based on type
        files: dict[str, Any] | None = None
        if connector_type == "localfile":
            pass
        elif connector_type == "s3":
            _, connection_data = input_connector.get_file_data()
            data["input_connection_data"] = json.dumps(connection_data)
        else:
            raise ValidationError(f"Unsupported connector type: {connector_type}")

        response = self._rate_limiter.submit_parse_job_request(
            connector_type=connector_type,
            input_connector=input_connector,
            data=data,
            files=files,
        )

        # Return job from response
        if "job_id" in response:
            return self._get_parse_job_details(response["job_id"])

        job_data = extract_job_data(response, primary_key="parse_job")
        return ParseJob.from_dict(job_data)

    def _get_parse_job_details(self, job_id: str) -> ParseJob:
        """Get current parse-job details."""
        response = self._request("GET", build_job_resource_path(job_id, PARSE_JOBS_PATH))
        job_data = extract_job_data(response, primary_key="parse_job")
        return ParseJob.from_dict(job_data)

    def _get_job_status(self, job_id: str) -> JobStatus:
        """Get lightweight processing status from the generic jobs endpoint."""
        response = self._request("GET", build_job_status_path(job_id))
        return JobStatus.from_dict(response)

    def _get_job_processing_status(self, job_id: str) -> JobStatus:
        """Backward-compatible alias for the lightweight status endpoint."""
        return self._get_job_status(job_id)

    def _list_parse_jobs(self) -> JobList:
        """List all parse jobs."""
        response = self._request("GET", build_job_collection_path(PARSE_JOBS_PATH))
        return JobList.from_dict(response)

    def _download_parse_result(
        self,
        job_id: str,
        result_format: OutputFormat | None = None,
    ) -> bytes:
        """Download parse job result."""
        url = build_url(self.BASE_URL, build_job_result_path(job_id, PARSE_JOBS_PATH))
        params = (
            {"output_format": result_format.value} if result_format is not None else {}
        )
        response = self._session.get(url, params=params, timeout=self.DEFAULT_TIMEOUT)
        if response.status_code not in (200, 201):
            handle_response(response)

        content_disposition = response.headers.get("Content-Disposition", "")
        content_type = response.headers.get("Content-Type", "")

        # Check if file download
        if "attachment" in content_disposition:
            return response.content

        # Handle JSON response (not ready or error)
        if "application/json" in content_type:
            data = handle_response(response)
            if not data.get("ready", False):
                status = data.get("processing_status", "unknown")
                raise JobProcessingError(f"Result not available. Job status: {status}")
            raise JobProcessingError("Job ready but no result file returned")

        # File response
        return response.content

    # ==================== BACKWARD-COMPAT FORWARDERS ====================

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Forward to the extracted HTTP helper."""
        return handle_response(response)

    def _wait_for_completion(
        self,
        job_id: str,
        input_connector: InputConnector | None = None,
        job: ParseJob | None = None,
    ) -> ParseJob:
        """Forward to the extracted polling helper."""
        return wait_for_completion(
            self._get_job_processing_status,
            job_id,
            input_connector=input_connector,
            job=job,
        )

    def _wait_for_extract_completion(self, job_id: str, job: ExtractJob) -> ExtractJob:
        """Forward to the extracted polling helper."""
        return wait_for_extract_completion(
            self._get_job_processing_status,
            job_id,
            job,
        )

    def _wait_for_custom_job_completion(self, job_id: str, job: CustomJob) -> CustomJob:
        """Forward to the extracted polling helper."""
        return wait_for_custom_job_completion(
            self._get_job_processing_status,
            job_id,
            job,
        )

    def _wait_for_classification_job_completion(
        self,
        job_id: str,
        job: ClassificationJob,
    ) -> ClassificationJob:
        """Poll the classification-job resource until it finishes."""

        def _get_classification_status(polled_job_id: str) -> JobStatus:
            details = self._get_classification_job_details(polled_job_id)
            return JobStatus(processing_status=details.processing_status)

        return wait_for_classification_job_completion(
            _get_classification_status,
            job_id,
            job,
        )

    # ==================== HTTP HELPERS ====================

    def _build_url(self, path: str) -> str:
        """Build full URL."""
        return build_url(self.BASE_URL, path)

    def _normalize_schema_name(self, name: str) -> str:
        """Normalize a saved-schema name before sending it to the API."""
        if not isinstance(name, str):
            raise ValidationError("name must be a non-empty string")

        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("name must be a non-empty string")

        return normalized_name

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make HTTP request."""
        url = self._build_url(path)
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)
        response = self._session.request(method, url, **kwargs)
        return handle_response(response)

    # ==================== CONTEXT MANAGER ====================

    def close(self):
        """Close HTTP session."""
        self._session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()
