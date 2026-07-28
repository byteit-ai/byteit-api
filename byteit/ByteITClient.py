"""ByteIT API client."""

import json
import time
from collections.abc import Callable
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any
from urllib.parse import quote

import requests

from .connectors import (
    InputConnector,
    LocalFileInputConnector,
    LocalFileOutputConnector,
    OutputConnector,
)
from .exceptions import (
    APIKeyError,
    AuthenticationError,
    ByteITError,
    JobProcessingError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)
from .models.CustomJob import CustomJob
from .models.CustomJobList import CustomJobList
from .models.DocumentType import DocumentType
from .models.ExtractJob import ExtractJob
from .models.ExtractJobList import ExtractJobList
from .models.JobList import JobList
from .models.JobStatus import JobStatus
from .models.OutputFormat import OutputFormat
from .models.ParseJob import ParseJob
from .models.ProcessingOptions import ProcessingOptions
from .models.SavedSchema import SavedSchema
from .models.SavedSchemaList import SavedSchemaList
from .progress import ProgressTracker
from .validations import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILES_PER_REQUEST,
    MAX_TOTAL_REQUEST_BYTES,
)

# API configuration
API_VERSION = "v1"
API_BASE = f"/{API_VERSION}"
JOBS_PATH = "jobs"
PARSE_JOBS_PATH = "parse-jobs"
EXTRACT_JOBS_PATH = "extract-jobs"
SCHEMAS_PATH = "schemas"
CUSTOM_JOBS_PATH = "custom-jobs"


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
        self._rate_limit_max_retries = rate_limit_max_retries
        self._rate_limit_base_delay = rate_limit_base_delay
        self._rate_limit_max_delay = rate_limit_max_delay
        self._batch_request_delay = batch_request_delay
        self._submission_delay = 0.0
        self._last_submission_at: float | None = None
        self._session = requests.Session()
        self._session.headers.update({"X-API-Key": self.api_key})

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
                ``extraction_type`` (str or ExtractionType).
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
                ``extraction_type`` (str or ExtractionType).
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
            if not self._is_duplicate_saved_schema_error(exc):
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

            response = self._submit_multi_file_batch(batch, data)
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

    def _submit_multi_file_batch(
        self,
        file_paths: list[Path],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit one multi-file request, retrying/spacing when rate limited."""
        for attempt in range(self._rate_limit_max_retries + 1):
            try:
                with ExitStack() as stack:
                    request_files = []
                    for path in file_paths:
                        handle = stack.enter_context(path.open("rb"))
                        request_files.append(("files", (path.name, handle)))

                    self._wait_before_submission()
                    response = self._request(
                        "POST",
                        self._build_job_collection_path(PARSE_JOBS_PATH),
                        files=request_files,
                        data=data,
                    )
                self._record_successful_submission()
                return response
            except RateLimitError as exc:
                if attempt >= self._rate_limit_max_retries:
                    raise
                delay = self._backoff_after_rate_limit(exc)
                print(
                    "Rate limited. Waiting "
                    f"{delay:.1f}s before retry "
                    f"({attempt + 1}/{self._rate_limit_max_retries})..."
                )
                time.sleep(delay)

        raise RateLimitError("Rate limit exceeded after retries.", status_code=429)

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
            self._build_job_collection_path(EXTRACT_JOBS_PATH),
            json={
                "parse_job_id": parse_job_id,
                "schema": schema_dict,
                "extraction_complexity": extraction_complexity,
            },
        )
        job_data = self._extract_job_data(response, primary_key="extract_job")
        return ExtractJob.from_dict(job_data)

    def _list_extract_jobs(self) -> ExtractJobList:
        """List all extract jobs."""
        response = self._request(
            "GET", self._build_job_collection_path(EXTRACT_JOBS_PATH)
        )
        return ExtractJobList.from_dict(response)

    def _get_extract_job_details(self, job_id: str) -> ExtractJob:
        """Get current extract-job details."""
        response = self._request(
            "GET", self._build_job_resource_path(job_id, EXTRACT_JOBS_PATH)
        )
        job_data = self._extract_job_data(response, primary_key="extract_job")
        return ExtractJob.from_dict(job_data)

    def _download_extract_result(self, job_id: str) -> dict[str, Any]:
        """Download the JSON result of a completed extraction job."""
        data = self._request(
            "GET", self._build_job_result_path(job_id, EXTRACT_JOBS_PATH)
        )
        data = data if isinstance(data, dict) else {}
        if not data.get("ready", True):
            status = data.get("processing_status", "unknown")
            raise JobProcessingError(f"Result not available. Job status: {status}")

        result = data.get("result", data)
        if not isinstance(result, dict):
            return data
        return result

    def _poll_until(
        self,
        job_id: str,
        job: Any,
        update_snapshot: Callable[[Any, JobStatus], Any],
        error_prefix: str = "Job",
        tracker: ProgressTracker | None = None,
    ) -> Any:
        """Adaptive polling loop shared by parse, extract, and custom jobs."""
        iteration = 1
        job_snapshot = job

        while True:
            status = self._get_job_processing_status(job_id)
            if isinstance(status, dict):
                status = JobStatus.from_dict(status)

            job_snapshot = update_snapshot(job_snapshot, status)

            if tracker:
                tracker.update(job_snapshot)

            if status.is_completed:
                if tracker:
                    tracker.finalize()
                return job_snapshot

            if status.is_failed:
                if tracker:
                    tracker.close()
                raise JobProcessingError(
                    f"{error_prefix} failed: {status.message or 'Unknown error'}"
                )

            poll_interval = min(1 * (1.5 ** (iteration - 1)), 10)
            time.sleep(poll_interval)
            iteration += 1

    def _wait_for_extract_completion(self, job_id: str, job: ExtractJob) -> ExtractJob:
        """Wait for an extraction job to complete with adaptive polling."""

        def _update(j: ExtractJob, s: JobStatus) -> ExtractJob:
            import dataclasses

            return dataclasses.replace(
                j,
                processing_status=s.processing_status,
            )

        return self._poll_until(
            job_id,
            job,
            _update,
            error_prefix="Extraction job",
        )

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
            self._build_schema_collection_path(),
            json={"name": name, "schema_json": schema_json},
        )
        return SavedSchema.from_dict(response)

    def _list_saved_schemas(self) -> SavedSchemaList:
        """List all saved schemas for the authenticated user."""
        response = self._request("GET", self._build_schema_collection_path())
        return SavedSchemaList.from_dict(response)

    def _get_saved_schema(self, name: str) -> SavedSchema:
        """Retrieve a saved schema by name."""
        response = self._request("GET", self._build_schema_resource_path(name))
        return SavedSchema.from_dict(response)

    def _delete_saved_schema(self, name: str) -> bool:
        """Delete a saved schema by name."""
        self._request("DELETE", self._build_schema_resource_path(name))
        return True

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
                self._build_job_collection_path(CUSTOM_JOBS_PATH),
                files=multipart_files,
                data=data,
            )
        finally:
            for file_obj in file_handles:
                if file_obj and hasattr(file_obj, "close") and not file_obj.closed:
                    file_obj.close()

        job_data = self._extract_job_data(response, primary_key="custom_job")
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
            self._build_job_collection_path(CUSTOM_JOBS_PATH),
            params=params or None,
        )
        return CustomJobList.from_dict(response)

    def _download_custom_job_result(self, job_id: str) -> bytes:
        """Download the raw result bytes of a completed custom job."""
        url = self._build_url(self._build_job_result_path(job_id, CUSTOM_JOBS_PATH))
        response = self._session.get(url, timeout=self.DEFAULT_TIMEOUT)
        if response.status_code not in (200, 201):
            self._handle_response(response)

        content_disposition = response.headers.get("Content-Disposition", "")
        content_type = response.headers.get("Content-Type", "")

        if "attachment" in content_disposition:
            if not response.content:
                raise JobProcessingError("Custom job result is empty")
            return response.content

        if "application/json" in content_type:
            data = self._handle_response(response)
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

    def _wait_for_custom_job_completion(
        self,
        job_id: str,
        job: CustomJob,
    ) -> CustomJob:
        """Wait for a custom job to complete with adaptive polling."""

        def _update(j: CustomJob, s: JobStatus) -> CustomJob:
            import dataclasses

            return dataclasses.replace(j, processing_status=s.processing_status)

        return self._poll_until(
            job_id,
            job,
            _update,
            error_prefix="Custom job",
        )

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

        response = self._submit_parse_job_request(
            connector_type=connector_type,
            input_connector=input_connector,
            data=data,
            files=files,
        )

        # Return job from response
        if "job_id" in response:
            return self._get_parse_job_details(response["job_id"])

        job_data = self._extract_job_data(response, primary_key="parse_job")
        return ParseJob.from_dict(job_data)

    def _get_parse_job_details(self, job_id: str) -> ParseJob:
        """Get current parse-job details."""
        response = self._request(
            "GET", self._build_job_resource_path(job_id, PARSE_JOBS_PATH)
        )
        job_data = self._extract_job_data(response, primary_key="parse_job")
        return ParseJob.from_dict(job_data)

    def _get_job_status(self, job_id: str) -> JobStatus:
        """Get lightweight processing status from the generic jobs endpoint."""
        response = self._request("GET", self._build_job_status_path(job_id))
        return JobStatus.from_dict(response)

    def _get_job_processing_status(self, job_id: str) -> JobStatus:
        """Backward-compatible alias for the lightweight status endpoint."""
        return self._get_job_status(job_id)

    def _list_parse_jobs(self) -> JobList:
        """List all parse jobs."""
        response = self._request("GET", self._build_job_collection_path(PARSE_JOBS_PATH))
        return JobList.from_dict(response)

    def _wait_for_completion(
        self,
        job_id: str,
        input_connector: InputConnector | None = None,
        job: ParseJob | None = None,
    ) -> ParseJob:
        """Wait for job to complete with adaptive polling: MIN(1*1.5^(x-1), 10)."""
        tracker = ProgressTracker(input_connector)

        def _update(j: ParseJob | None, s: JobStatus) -> ParseJob:
            return self._merge_job_status(job_id, s, j)

        initial = job
        return self._poll_until(
            job_id,
            initial,
            _update,
            error_prefix="Job",
            tracker=tracker,
        )

    def _download_parse_result(
        self,
        job_id: str,
        result_format: OutputFormat | None = None,
    ) -> bytes:
        """Download parse job result."""
        url = self._build_url(self._build_job_result_path(job_id, PARSE_JOBS_PATH))
        params = (
            {"output_format": result_format.value} if result_format is not None else {}
        )
        response = self._session.get(url, params=params, timeout=self.DEFAULT_TIMEOUT)
        if response.status_code not in (200, 201):
            self._handle_response(response)

        content_disposition = response.headers.get("Content-Disposition", "")
        content_type = response.headers.get("Content-Type", "")

        # Check if file download
        if "attachment" in content_disposition:
            return response.content

        # Handle JSON response (not ready or error)
        if "application/json" in content_type:
            data = self._handle_response(response)
            if not data.get("ready", False):
                status = data.get("processing_status", "unknown")
                raise JobProcessingError(f"Result not available. Job status: {status}")
            raise JobProcessingError("Job ready but no result file returned")

        # File response
        return response.content

    # ==================== HTTP HELPERS ====================

    def _build_url(self, path: str) -> str:
        """Build full URL."""
        return f"{self.BASE_URL}/{path.lstrip('/')}"

    def _build_job_collection_path(self, job_type: str | None = None) -> str:
        """Build a collection path under the jobs API namespace."""
        segments = [API_BASE, JOBS_PATH]
        if job_type:
            segments.append(job_type)
        return "/" + "/".join(segment.strip("/") for segment in segments) + "/"

    def _build_job_resource_path(self, job_id: str, job_type: str | None = None) -> str:
        """Build a resource path for a specific job type."""
        return f"{self._build_job_collection_path(job_type)}{job_id}/"

    def _build_job_result_path(self, job_id: str, job_type: str | None = None) -> str:
        """Build a result download path for a specific job type."""
        return f"{self._build_job_resource_path(job_id, job_type)}result/"

    def _build_job_status_path(self, job_id: str) -> str:
        """Build the generic jobs processing-status path."""
        return f"{self._build_job_resource_path(job_id)}status/"

    def _build_schema_collection_path(self) -> str:
        """Build the saved-schema collection path."""
        segments = [API_BASE, SCHEMAS_PATH]
        return "/" + "/".join(segment.strip("/") for segment in segments) + "/"

    def _build_schema_resource_path(self, name: str) -> str:
        """Build the saved-schema resource path for a schema name."""
        normalized_name = self._normalize_schema_name(name)
        encoded_name = quote(normalized_name, safe="")
        return f"{self._build_schema_collection_path()}{encoded_name}/"

    def _extract_job_data(
        self,
        response: dict[str, Any],
        primary_key: str,
    ) -> dict[str, Any]:
        """Extract a job payload from known API response shapes."""
        return response.get(
            primary_key,
            response.get("job", response.get("document", response)),
        )

    def _normalize_schema_name(self, name: str) -> str:
        """Normalize a saved-schema name before sending it to the API."""
        if not isinstance(name, str):
            raise ValidationError("name must be a non-empty string")

        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("name must be a non-empty string")

        return normalized_name

    def _is_duplicate_saved_schema_error(self, error: ValidationError) -> bool:
        """Return True when a validation error represents duplicate saved-schema name."""
        if error.status_code != 400:
            return False

        error_message = (error.message or "").lower()
        return "schema" in error_message and "already exists" in error_message

    def _merge_job_status(
        self,
        job_id: str,
        status: JobStatus | dict[str, Any],
        job: ParseJob | None,
    ) -> ParseJob:
        """Project a lightweight status response onto a ParseJob-shaped object."""
        if isinstance(status, dict):
            status = JobStatus.from_dict(status)

        if job is None:
            return ParseJob(
                id=job_id,
                processing_status=status.processing_status,
                result_format="",
                processing_error=status.message,
            )

        import dataclasses

        return dataclasses.replace(
            job,
            processing_status=status.processing_status,
            processing_error=status.message or job.processing_error,
        )

    def _submit_parse_job_request(
        self,
        connector_type: str,
        input_connector: InputConnector,
        data: dict[str, Any],
        files: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Submit a parse job, retrying and spacing requests when rate limited."""
        for attempt in range(self._rate_limit_max_retries + 1):
            file_obj = None
            request_files = files
            try:
                if connector_type == "localfile":
                    filename, file_obj = input_connector.get_file_data()
                    request_files = {"file": (filename, file_obj)}

                self._wait_before_submission()
                response = self._request(
                    "POST",
                    self._build_job_collection_path(PARSE_JOBS_PATH),
                    files=request_files,
                    data=data,
                )
                self._record_successful_submission()
                return response
            except RateLimitError as exc:
                if attempt >= self._rate_limit_max_retries:
                    raise
                delay = self._backoff_after_rate_limit(exc)
                print(
                    "Rate limited. Waiting "
                    f"{delay:.1f}s before retry "
                    f"({attempt + 1}/{self._rate_limit_max_retries})..."
                )
                time.sleep(delay)
            finally:
                if file_obj and hasattr(file_obj, "close") and not file_obj.closed:
                    file_obj.close()

        raise RateLimitError("Rate limit exceeded after retries.", status_code=429)

    def _wait_before_submission(self) -> None:
        """Sleep when a previous rate limit requires spacing between submissions."""
        if self._submission_delay <= 0 or self._last_submission_at is None:
            return

        elapsed = time.monotonic() - self._last_submission_at
        wait_time = self._submission_delay - elapsed
        if wait_time > 0:
            time.sleep(wait_time)

    def _record_successful_submission(self) -> None:
        """Track submission timing and gradually reduce adaptive throttling."""
        self._last_submission_at = time.monotonic()
        if self._submission_delay > self._rate_limit_base_delay:
            self._submission_delay = max(
                self._rate_limit_base_delay,
                self._submission_delay * 0.5,
            )

    def _backoff_after_rate_limit(self, error: RateLimitError) -> float:
        """Increase spacing between submissions and return the wait duration."""
        suggested_delay = error.retry_after_seconds or self._rate_limit_base_delay
        if self._submission_delay <= 0:
            self._submission_delay = min(suggested_delay, self._rate_limit_max_delay)
        else:
            self._submission_delay = min(
                max(self._submission_delay * 2, suggested_delay),
                self._rate_limit_max_delay,
            )
        return max(suggested_delay, self._submission_delay)

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        """Parse a Retry-After header value into seconds."""
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make HTTP request."""
        url = self._build_url(path)
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)
        response = self._session.request(method, url, **kwargs)
        return self._handle_response(response)

    @staticmethod
    def _extract_error_message(
        data: dict[str, Any],
        response: requests.Response,
    ) -> str:
        """Return a human-readable API error message from a JSON error body."""
        for key in ("detail", "error"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value

        if response.text:
            return response.text

        return f"Request failed with status {response.status_code}"

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        # Success path
        if response.status_code in (200, 201, 204):
            return response.json() if response.content else {}

        # Error path - extract details
        try:
            data: dict[str, Any] = response.json() if response.content else {}
            message: str = (
                data.get("detail", "")
                or data.get("error", "")
                or response.text
                or "Request failed"
            )
        except (ValueError, requests.exceptions.JSONDecodeError):
            # Response is not JSON (e.g., HTML error page)
            data = {}
            message = self._extract_error_message(data, response)

        if response.status_code == 429:
            retry_after = self._parse_retry_after(response.headers.get("Retry-After"))
            raise RateLimitError(
                message,
                response.status_code,
                data,
                retry_after_seconds=retry_after,
            )

        # Map status to exception
        ERROR_MAP: dict[int, type[Exception]] = {  # noqa: N806
            400: ValidationError,
            401: AuthenticationError,
            403: APIKeyError,
            404: ResourceNotFoundError,
        }

        ExceptionClass = ERROR_MAP.get(response.status_code)  # noqa: N806
        if ExceptionClass:
            raise ExceptionClass(message, response.status_code, data)

        if response.status_code >= 500:
            raise ServerError(message, response.status_code, data)

        raise ByteITError(message, response.status_code, data)

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
