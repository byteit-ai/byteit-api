"""ByteIT API client."""

import json
import time
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

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
from .models.JobList import JobList
from .models.JobStatus import JobStatus
from .models.OutputFormat import OutputFormat
from .models.ParseJob import ParseJob
from .models.ProcessingOptions import ProcessingOptions
from .progress import ProgressTracker

# API configuration
API_VERSION = "v1"
API_BASE = f"/{API_VERSION}"
JOBS_PATH = "jobs"
PARSE_JOBS_PATH = "parse-jobs"


class ByteITClient:
    """Client for ByteIT document parsing.

    Provides both synchronous and asynchronous document parsing workflows.

    Methods:
        parse(input, ...):           Parse a document and wait for the result.
        parse_async(input, ...):     Submit a document for parsing, return.
        get_job_details(job_id):     Get the full parse-job resource.
        get_job_status(job_id):      Check the lightweight processing status.
        get_job_result(job_id):      Download the result of a completed job.
        get_jobs():                  List all jobs for your account.

    Examples:
        Synchronous (blocking)::

            client = ByteITClient(api_key="your_key") result =
            client.parse("document.pdf")

        Asynchronous (non-blocking)::

            job = client.parse_async("document.pdf") # ... do other work ...
            status = client.get_job_status(job.id) if status.is_completed:
                details = client.get_job_details(job.id)
                result = client.get_job_result(details.id)
    """

    # BASE_URL = "https://api.byteit.ai"
    # BASE_URL = "http://127.0.0.1:8000"
    BASE_URL = "https://byteit.ai"
    DEFAULT_TIMEOUT = 60 * 30  # 30 minutes

    def __init__(self, api_key: str):
        """Initialize the ByteIT client.

        Args:
            api_key: Your ByteIT API key

        Raises:
            APIKeyError: If API key is invalid
        """
        if not api_key:
            raise APIKeyError("API key must be a non-empty string")

        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({"X-API-Key": self.api_key})

    # ==================== PUBLIC API ====================

    def parse(
        self,
        input: str | Path | InputConnector,
        output: None | str | Path = None,
        processing_options: ProcessingOptions | dict | None = None,
        result_format: str | OutputFormat = OutputFormat.MD,
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
            result_format: Output format enum. Supported values are
                ``OutputFormat.TXT``, ``OutputFormat.JSON``,
                ``OutputFormat.MD``, ``OutputFormat.HTML``, and
                ``OutputFormat.EXCEL``.

        Returns:
            Parsed content as bytes.
            IMPORTANT: If output format is set to EXCEL,
            it returns bytes of a zip file containing the Excel file.

        Example::

            result = client.parse("document.pdf")
            client.parse("doc.pdf", output="result.md")
            client.parse("doc.pdf", result_format=OutputFormat.JSON)
        """
        result_format = self._parse_output_format(result_format)
        job, input_connector = self._submit_job(
            input, processing_options, result_format, output
        )
        print(f"Job {job.id} created. Waiting for completion...")
        self._wait_for_completion(job.id, input_connector=input_connector, job=job)

        # Download result
        result_bytes = self._download_result(job.id)

        # If output is a file path, save it
        if isinstance(output, (str, Path)):
            Path(output).write_bytes(result_bytes)
        elif output is None:
            self._try_display_result(result_bytes, result_format)

        return result_bytes

    def parse_async(
        self,
        input: str | Path | InputConnector,
        processing_options: ProcessingOptions | dict | None = None,
        result_format: str | OutputFormat = OutputFormat.MD,
    ) -> ParseJob:
        """Submit a document for parsing and return immediately.

        Use this for non-blocking workflows. Check progress with
        :meth:`get_job_status`, inspect metadata with :meth:`get_job_details`,
        and retrieve results with :meth:`get_job_result`.

        Args:
            input: File path (str/Path) or InputConnector.
            processing_options: ProcessingOptions or dict with keys:
                ``languages`` (list[str]), ``page_range`` (str), and
                ``extraction_type`` (str or ExtractionType).
            result_format: Output format enum. Supported values are
                ``OutputFormat.TXT``, ``OutputFormat.JSON``,
                ``OutputFormat.MD``, ``OutputFormat.HTML``, and
                ``OutputFormat.EXCEL``.

        Returns:
            ParseJob object with ``id``, ``processing_status``, and other metadata.

        Example::

            job = client.parse_async("document.pdf")
            # ... do other work ...
            status = client.get_job_status(job.id)
            if status.is_completed:
                result = client.get_job_result(job.id)
        """
        result_format = self._parse_output_format(result_format)
        job, _ = self._submit_job(input, processing_options, result_format)
        print(f"Job {job.id} submitted.")
        return job

    def get_jobs(self) -> JobList:
        """List all jobs for your account.

        Returns:
            JobList response with collection metadata and jobs.

        Example::

            job_list = client.get_jobs()
            for job in job_list.jobs:
                print(f"{job.id}: {job.processing_status}")
        """
        return self._list_jobs()

    def get_job_details(self, job_id: str) -> ParseJob:
        """Get the full parse-job resource for a job.

        Args:
            job_id: The job ID.

        Returns:
            ParseJob object with backend detail fields and metadata.

        Example::

            job = client.get_job_details("job_123")
            print(job.result_format)
        """
        return self._get_job_details(job_id)

    def get_job_status(self, job_id: str) -> JobStatus:
        """Check the lightweight processing status of a job.

        Args:
            job_id: The job ID.

        Returns:
            JobStatus object with progress, status, and backend message.

        Example::

            status = client.get_job_status("job_123")
            if status.is_completed:
                result = client.get_job_result("job_123")
        """
        return self._get_job_status(job_id)

    def get_job_result(self, job_id: str) -> bytes:
        """Download the result of a completed job.

        Args:
            job_id: The job ID.

        Returns:
            Parsed content as bytes.

        Raises:
            JobProcessingError: If the job has not completed yet.

        Example::

            result = client.get_job_result("job_123")
            with open("output.md", "wb") as f:
                f.write(result)
        """
        return self._download_result(job_id)

    # ==================== JOB SUBMISSION ====================

    def _submit_job(
        self,
        input: str | Path | InputConnector,
        processing_options: ProcessingOptions | dict | None = None,
        result_format: OutputFormat = OutputFormat.MD,
        output: None | str | Path = None,
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
            result_format=result_format,
        )
        return job, input_connector

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
                if normalized_result_format == output_format.name.lower() or (
                    output_format is not OutputFormat.EXCEL
                    and normalized_result_format == output_format.value.lower()
                ):
                    return output_format

        supported_formats = ", ".join(
            output_format.name.lower() for output_format in OutputFormat
        )
        raise ValidationError(
            f"result_format must be an OutputFormat or one of: {supported_formats}"
        )

    # ==================== INTERNAL METHODS ====================

    def _create_job(
        self,
        input_connector: InputConnector,
        output_connector: OutputConnector,
        result_format: OutputFormat,
        processing_options: ProcessingOptions | None = None,
    ) -> ParseJob:
        """Create a processing job."""
        connector_type = (
            input_connector.to_dict().get("type", "localfile").strip().lower()
        )

        # Build base request data
        data: dict[str, Any] = {
            "output_format": result_format.value,
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

        # Prepare input based on type
        files: dict[str, Any] | None = None
        file_obj = None

        if connector_type == "localfile":
            filename, file_obj = input_connector.get_file_data()
            files = {"file": (filename, file_obj)}
        elif connector_type == "s3":
            _, connection_data = input_connector.get_file_data()
            data["input_connection_data"] = json.dumps(connection_data)
        else:
            raise ValidationError(f"Unsupported connector type: {connector_type}")

        # Make request with cleanup
        try:
            response = self._request(
                "POST",
                self._build_job_collection_path(PARSE_JOBS_PATH),
                files=files,
                data=data,
            )
        finally:
            if file_obj and hasattr(file_obj, "close") and not file_obj.closed:
                file_obj.close()

        # Return job from response
        if "job_id" in response:
            return self._get_job_details(response["job_id"])

        job_data = self._extract_job_data(response, primary_key="parse_job")
        return ParseJob.from_dict(job_data)

    def _get_job_details(self, job_id: str) -> ParseJob:
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

    def _list_jobs(self) -> JobList:
        """List all jobs."""
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
        iteration = 1
        job_snapshot = job

        while True:
            status = self._get_job_processing_status(job_id)
            if isinstance(status, dict):
                status = JobStatus.from_dict(status)
            job_snapshot = self._merge_job_status(job_id, status, job_snapshot)
            tracker.update(job_snapshot)

            if status.is_completed:
                tracker.finalize()
                return job_snapshot

            if status.is_failed:
                tracker.close()
                raise JobProcessingError(
                    f"Job failed: {job_snapshot.processing_error or 'Unknown error'}"
                )

            poll_interval = min(1 * (1.5 ** (iteration - 1)), 10)
            time.sleep(poll_interval)
            iteration += 1

    def _download_result(self, job_id: str) -> bytes:
        """Download job result."""
        url = self._build_url(self._build_job_result_path(job_id, PARSE_JOBS_PATH))
        response = self._session.get(url, timeout=self.DEFAULT_TIMEOUT)
        response.raise_for_status()

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

    def _merge_job_status(
        self,
        job_id: str,
        status: JobStatus | dict[str, Any],
        job: ParseJob | None,
    ) -> ParseJob:
        """Project a lightweight status response onto a ParseJob-shaped object."""
        if isinstance(status, dict):
            status = JobStatus.from_dict(status)

        processing_status = status.processing_status
        processing_error = status.message

        if job is None:
            return ParseJob(
                id=job_id,
                processing_status=processing_status,
                result_format="",
                create_time=datetime.now(),
                update_time=datetime.now(),
                processing_error=processing_error,
            )

        return ParseJob(
            id=job.id,
            processing_status=processing_status,
            result_format=job.result_format,
            name=job.name,
            uid=job.uid,
            create_time=job.create_time,
            update_time=job.update_time,
            delete_time=job.delete_time,
            nickname=job.nickname,
            metadata=job.metadata,
            processing_options=job.processing_options,
            processing_time_seconds=job.processing_time_seconds,
            processing_error=processing_error or job.processing_error,
            credits_cost=job.credits_cost,
            input_connector=job.input_connector,
            output_connector=job.output_connector,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make HTTP request."""
        url = self._build_url(path)
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)
        response = self._session.request(method, url, **kwargs)
        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        # Success path
        if response.status_code in (200, 201):
            return response.json() if response.content else {}

        # Error path - extract details
        try:
            data: dict[str, Any] = response.json() if response.content else {}
            message: str = data.get("detail", "") or response.text or "Request failed"
        except (ValueError, requests.exceptions.JSONDecodeError):
            # Response is not JSON (e.g., HTML error page)
            data = {}
            message = (
                response.text or f"Request failed with status {response.status_code}"
            )

        # Map status to exception
        ERROR_MAP: dict[int, type[Exception]] = {  # noqa: N806
            400: ValidationError,
            401: AuthenticationError,
            403: APIKeyError,
            404: ResourceNotFoundError,
            429: RateLimitError,
        }

        ExceptionClass = ERROR_MAP.get(response.status_code)  # noqa: N806
        if ExceptionClass:
            raise ExceptionClass(message, response.status_code, data)

        if response.status_code >= 500:
            raise ServerError(message, response.status_code, data)

        raise ByteITError(message, response.status_code, data)

    def _try_display_result(
        self, result_bytes: bytes, result_format: OutputFormat
    ) -> None:
        """Try to display result in notebook environment."""
        if result_format is OutputFormat.EXCEL:
            return

        try:
            # Check if we're in a notebook environment
            from IPython.display import HTML, JSON, Markdown, display

            content = result_bytes.decode("utf-8", errors="replace")

            if result_format is OutputFormat.JSON:
                try:
                    data = json.loads(content)
                    display(JSON(data, expanded=True))
                except json.JSONDecodeError:
                    display(Markdown(f"```json\n{content}\n```"))
            elif result_format is OutputFormat.MD:
                display(Markdown(content))
            elif result_format is OutputFormat.HTML:
                display(HTML(content))
            else:  # txt or unknown
                display(Markdown(f"```\n{content}\n```"))
        except ImportError:
            # Not in a notebook, do nothing
            pass

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
