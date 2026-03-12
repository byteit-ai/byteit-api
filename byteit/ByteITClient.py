"""ByteIT API client."""  # noqa: N999

import json
import time
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
from .models.Job import Job
from .models.JobList import JobList
from .models.ProcessingOptions import ProcessingOptions
from .progress import ProgressTracker

# API configuration
API_VERSION = "v1"
API_BASE = f"/{API_VERSION}"
JOBS_PATH = "jobs"


class ByteITClient:
    """Client for ByteIT document parsing.

    Provides both synchronous and asynchronous document parsing workflows.

    Methods:
        parse(input, ...):           Parse a document and wait for the result.
        parse_async(input, ...):     Submit a document for parsing, return immediately.
        get_job_status(job_id):      Check the processing status of a job.
        get_job_result(job_id):      Download the result of a completed job.
        get_jobs():                  List all jobs for your account.

    Examples:
        Synchronous (blocking)::

            client = ByteITClient(api_key="your_key")
            result = client.parse("document.pdf")

        Asynchronous (non-blocking)::

            job = client.parse_async("document.pdf")
            # ... do other work ...
            status = client.get_job_status(job.id)
            if status.is_completed:
                result = client.get_job_result(job.id)
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
        result_format: str = "md",
    ) -> bytes:
        """Parse a document and wait for the result.

        Submits the document, polls until processing completes, and returns
        the parsed content. For non-blocking usage, see :meth:`parse_async`.

        Args:
            input: File path (str/Path) or InputConnector (e.g. S3InputConnector).
            output: Optional file path to save the result to disk.
            processing_options: ProcessingOptions or dict with keys:
                ``languages`` (list[str]), ``page_range`` (str).
            result_format: Output format: ``"txt"``, ``"json"``, ``"md"``,
                or ``"html"`` (default: ``"md"``).

        Returns:
            Parsed content as bytes.

        Example::

            result = client.parse("document.pdf")
            client.parse("doc.pdf", output="result.md")
            client.parse("doc.pdf", result_format="json")
        """
        job, input_connector = self._submit_job(
            input, processing_options, result_format, output
        )
        print(f"Job {job.id} created. Waiting for completion...")
        self._wait_for_completion(job.id, input_connector=input_connector)

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
        result_format: str = "md",
    ) -> Job:
        """Submit a document for parsing and return immediately.

        Use this for non-blocking workflows. Check progress with
        :meth:`get_job_status` and retrieve results with :meth:`get_job_result`.

        Args:
            input: File path (str/Path) or InputConnector (e.g. S3InputConnector).
            processing_options: ProcessingOptions or dict with keys:
                ``languages`` (list[str]), ``page_range`` (str).
            result_format: Output format: ``"txt"``, ``"json"``, ``"md"``,
                or ``"html"`` (default: ``"md"``).

        Returns:
            Job object with ``id``, ``processing_status``, and other metadata.

        Example::

            job = client.parse_async("document.pdf")
            # ... do other work ...
            status = client.get_job_status(job.id)
            if status.is_completed:
                result = client.get_job_result(job.id)
        """
        job, _ = self._submit_job(input, processing_options, result_format)
        print(f"Job {job.id} submitted.")
        return job

    def get_jobs(self) -> list[Job]:
        """List all jobs for your account.

        Returns:
            List of Job objects.

        Example::

            for job in client.get_jobs():
                print(f"{job.id}: {job.processing_status}")
        """
        job_list = self._list_jobs()
        return job_list.jobs

    def get_job_status(self, job_id: str) -> Job:
        """Check the processing status of a job.

        Args:
            job_id: The job ID.

        Returns:
            Job object with current status and metadata.

        Example::

            job = client.get_job_status("job_123")
            if job.is_completed:
                result = client.get_job_result(job.id)
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
        result_format: str = "md",
        output: None | str | Path = None,
    ) -> tuple[Job, InputConnector]:
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

    def _to_input_connector(
        self, input: str | Path | InputConnector
    ) -> InputConnector:
        """Convert various input types to InputConnector."""
        # Already a connector (checks for InputConnector or its subclasses)
        if isinstance(input, InputConnector):
            return input

        # String or Path - local file
        if not isinstance(input, (str, Path)):
            raise ValidationError(
                f"Unsupported input type: {type(input).__name__}"
            )

        return LocalFileInputConnector(file_path=str(input))

    def _to_output_connector(self, output: None | str | Path):  # noqa: ARG002
        """Convert output specification to OutputConnector."""
        # Always use ByteIT storage (simplest approach)
        # If output is a file path, we download and save after completion
        return LocalFileOutputConnector()

    # ==================== INTERNAL METHODS ====================

    def _create_job(
        self,
        input_connector: InputConnector,
        output_connector: OutputConnector,
        result_format: str,
        processing_options: ProcessingOptions | None = None,
    ) -> Job:
        """Create a processing job."""
        connector_type = (
            input_connector.to_dict().get("type", "localfile").strip().lower()
        )

        # Build base request data
        data: dict[str, Any] = {
            "output_format": result_format,
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
            raise ValidationError(
                f"Unsupported connector type: {connector_type}"
            )

        # Make request with cleanup
        try:
            response = self._request(
                "POST", f"{API_BASE}/{JOBS_PATH}/", files=files, data=data
            )
        finally:
            if file_obj and hasattr(file_obj, "close") and not file_obj.closed:
                file_obj.close()

        # Return job from response
        if "job_id" in response:
            return self._get_job_status(response["job_id"])

        return Job.from_dict(response["job"])

    def _get_job_status(self, job_id: str) -> Job:
        """Get current job status."""
        response = self._request("GET", f"{API_BASE}/{JOBS_PATH}/{job_id}/")
        job_data = response.get("job", response.get("document", response))
        return Job.from_dict(job_data)

    def _list_jobs(self) -> JobList:
        """List all jobs."""
        response = self._request("GET", f"{API_BASE}/{JOBS_PATH}/")
        jobs_data = response.get("jobs", response.get("documents", []))
        jobs = [Job.from_dict(doc) for doc in jobs_data]
        return JobList(
            jobs=jobs,
            count=response.get("count", len(jobs)),
            detail=response.get("detail", ""),
        )

    def _wait_for_completion(
        self, job_id: str, input_connector: InputConnector | None = None
    ) -> Job:
        """Wait for job to complete with adaptive polling: MIN(1*1.5^(x-1), 10)."""  # noqa: E501
        tracker = ProgressTracker(input_connector)
        iteration = 1

        while True:
            job = self._get_job_status(job_id)
            tracker.update(job)

            if job.is_completed:
                tracker.finalize()
                return job

            if job.is_failed:
                tracker.close()
                raise JobProcessingError(
                    f"Job failed: {job.processing_error or 'Unknown error'}"
                )

            poll_interval = min(1 * (1.5 ** (iteration - 1)), 10)
            time.sleep(poll_interval)
            iteration += 1

    def _download_result(self, job_id: str) -> bytes:
        """Download job result."""
        url = self._build_url(f"{API_BASE}/{JOBS_PATH}/{job_id}/result/")
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
                raise JobProcessingError(
                    f"Result not available. Job status: {status}"
                )
            raise JobProcessingError("Job ready but no result file returned")

        # File response
        return response.content

    # ==================== HTTP HELPERS ====================

    def _build_url(self, path: str) -> str:
        """Build full URL."""
        return f"{self.BASE_URL}/{path.lstrip('/')}"

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
            message: str = (
                data.get("detail", "") or response.text or "Request failed"
            )
        except (ValueError, requests.exceptions.JSONDecodeError):
            # Response is not JSON (e.g., HTML error page)
            data = {}
            message = (
                response.text
                or f"Request failed with status {response.status_code}"
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
        self, result_bytes: bytes, result_format: str
    ) -> None:
        """Try to display result in notebook environment."""
        try:
            # Check if we're in a notebook environment
            from IPython.display import HTML, JSON, Markdown, display

            content = result_bytes.decode("utf-8", errors="replace")

            if result_format == "json":
                import json

                try:
                    data = json.loads(content)
                    display(JSON(data, expanded=True))
                except json.JSONDecodeError:
                    display(Markdown(f"```json\n{content}\n```"))
            elif result_format == "md":
                display(Markdown(content))
            elif result_format == "html":
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
