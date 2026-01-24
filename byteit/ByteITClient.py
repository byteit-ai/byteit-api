"""Simplified ByteIT API client - clean and minimal."""

import json
import time
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Optional, Type, Union

import requests


from .connectors import (
    LocalFileOutputConnector,
    InputConnector,
    OutputConnector,
    LocalFileInputConnector,
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

# API configuration
API_VERSION = "v1"
API_BASE = f"/{API_VERSION}"
JOBS_PATH = "jobs"


class ByteITClient:
    """
    Simple client for ByteIT document parsing.

    Methods:
        - parse(): Parse a document and get the result
        - get_all_jobs(): Get all your jobs
        - get_job_by_id(): Get a specific job
        - get_result(): Download a job result

    Example:
        client = ByteITClient(api_key="your_key")
        result = client.parse("document.pdf")  # Returns bytes
        client.parse("doc.pdf", output="result.txt")  # Saves to file
    """

    # BASE_URL = "https://api.byteit.ai"
    # BASE_URL = "http://127.0.0.1:8000"
    BASE_URL = "https://heinzelai.com"
    DEFAULT_TIMEOUT = 60 * 10  # 10 minutes

    def __init__(self, api_key: str):
        """
        Initialize the ByteIT client.

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
        input: Union[str, Path, InputConnector],
        output: Union[None, str, Path] = None,
        result_format: str = "md",
    ) -> bytes:
        """
        Parse a document and wait for the result.

        Args:
            input: File to parse. Can be:
                - str or Path: Local file path
                - InputConnector: For S3 or custom sources
            result_format: "txt", "json", "md", or "html" (default: "txt")
            output: Where to save result (optional). Can be:
                - None: Return result as bytes (default)
                - str or Path: Save to local file

        Returns:
            Parsed content as bytes

        Example:
            # Simple - returns bytes
            result = client.parse("document.pdf")

            # Save to file
            client.parse("doc.pdf", output="result.txt")

            # S3 input (use connector)
            from byteit.connectors import S3InputConnector
            result = client.parse(S3InputConnector("my-bucket", "file.pdf"))

            # Different format
            json_result = client.parse("doc.pdf", result_format="json")
        """
        print("Starting document parsing...")
        # Convert input to connector as early as possible
        input_connector = self._to_input_connector(input)

        # Convert output to connector if provided
        output_connector = self._to_output_connector(output)

        # Create job and wait
        job = self._create_job(
            input_connector=input_connector,
            output_connector=output_connector,
            result_format=result_format,
        )
        print(f"Job {job.id} created. Waiting for completion...")
        self._wait_for_completion(job.id)

        # Download result
        result_bytes = self._download_result(job.id)

        # If output is a file path, save it
        if isinstance(output, (str, Path)):
            output_path = Path(output)
            output_path.write_bytes(result_bytes)

        return result_bytes

    def get_all_jobs(self) -> List[Job]:
        """
        Get all jobs for your account.

        Returns:
            List of Job objects

        Example:
            jobs = client.get_all_jobs()
            for job in jobs:
                print(f"{job.id}: {job.processing_status}")
        """
        job_list = self._list_jobs()
        return job_list.jobs

    def get_job_by_id(self, job_id: str) -> Job:
        """
        Get a specific job by ID.

        Args:
            job_id: The job ID

        Returns:
            Job object

        Example:
            job = client.get_job_by_id("job_123")
        """
        return self._get_job_status(job_id)

    def get_result(self, job_id: str) -> bytes:
        """
        Download result for a completed job.

        Args:
            job_id: The job ID

        Returns:
            Result as bytes

        Raises:
            JobProcessingError: If job is not completed
        """
        return self._download_result(job_id)

    # ==================== CONNECTOR CONVERTERS ====================

    def _to_input_connector(self, input: Union[str, Path, InputConnector]) -> InputConnector:
        """Convert various input types to InputConnector."""
        # Already a connector (checks for InputConnector or its subclasses)
        if isinstance(input, InputConnector):
            return input

        # String or Path - local file
        return LocalFileInputConnector(file_path=str(input))

    def _to_output_connector(self, output: Union[None, str, Path]):
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
    ) -> Job:
        """Create a processing job."""
        connector_type = input_connector.to_dict().get("type", "localfile").strip().lower()

        # Build base request data
        data: Dict[str, Any] = {
            "output_format": result_format,
            "processing_options": json.dumps({}),
            "input_connector": connector_type,
        }

        # Add output connector config
        output_config = output_connector.to_dict()
        data["output_connector"] = output_config.get("type", "")
        data["output_connection_data"] = (
            json.dumps(output_config) if output_config.get("type") else "{}"
        )

        # Prepare input based on type
        files: Optional[Dict[str, Any]] = None
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
            response = self._request("POST", f"{API_BASE}/{JOBS_PATH}/", files=files, data=data)
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

    def _wait_for_completion(self, job_id: str) -> Job:
        """Wait for job to complete (polls every 2 seconds)."""
        MAX_INTERVAL = 10  # Max 10 seconds
        poll_interval = 2  # Start at 2 seconds

        while True:
            job = self._get_job_status(job_id)

            if job.is_completed:
                return job

            if job.is_failed:
                raise JobProcessingError(f"Job failed: {job.processing_error or 'Unknown error'}")

            time.sleep(poll_interval)
            poll_interval = min(poll_interval + 1, MAX_INTERVAL)

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
                raise JobProcessingError(f"Result not available. Job status: {status}")
            raise JobProcessingError("Job ready but no result file returned")

        # File response
        return response.content

    # ==================== HTTP HELPERS ====================

    def _build_url(self, path: str) -> str:
        """Build full URL."""
        return f"{self.BASE_URL}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make HTTP request."""
        url = self._build_url(path)
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)
        response = self._session.request(method, url, **kwargs)
        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        # Success path
        if response.status_code in (200, 201):
            return response.json() if response.content else {}

        # Error path - extract details
        try:
            data: Dict[str, Any] = response.json() if response.content else {}
            message: str = data.get("detail", "") or response.text or "Request failed"
        except (ValueError, requests.exceptions.JSONDecodeError):
            # Response is not JSON (e.g., HTML error page)
            data = {}
            message = response.text or f"Request failed with status {response.status_code}"

        # Map status to exception
        ERROR_MAP: Dict[int, Type[Exception]] = {
            400: ValidationError,
            401: AuthenticationError,
            403: APIKeyError,
            404: ResourceNotFoundError,
            429: RateLimitError,
        }

        ExceptionClass = ERROR_MAP.get(response.status_code)
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
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        self.close()
