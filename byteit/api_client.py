"""Main API client for ByteIT text extraction service."""

import time
from pathlib import Path
from typing import Any, Dict, Optional, Union, cast, Type

import requests

from types import TracebackType

from .exceptions import (
    APIKeyError,
    AuthenticationError,
    ByteITError,
    JobProcessingError,
    NetworkError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)
from .models import Job, JobList
from .connectors import (
    InputConnector,
    OutputConnector,
    ByteITStorageOutputConnector,
)
from .validation import validate_processing_options


# API path constants so endpoints can be changed in one place
API_VERSION = "v1"
API_BASE = f"/{API_VERSION}"
JOBS_PATH = "jobs"


class ByteITClient:
    """
    Client for interacting with the ByteIT text extraction API.
    """

    # BASE_URL = "https://api.byteit.ai"
    BASE_URL = "http://127.0.0.1:8000"  # Temporary during development
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        api_key: str,
    ):
        """
        Initialize the ByteIT client.

        Args:
            api_key: Your ByteIT API key in format <id>.<secret>

        Raises:
            APIKeyError: If the API key format is invalid
        """
        if not api_key:
            raise APIKeyError("API key must be a non-empty string")

        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-API-Key": self.api_key,
            }
        )

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        return f"{self.BASE_URL}/{path.lstrip('/')}"

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: The response object from requests

        Returns:
            The JSON response data

        Raises:
            Various ByteITError subclasses based on status code
        """
        # Initialize as Any so static checkers don't infer a union type from the branches
        data_raw: Any = {}
        try:
            # Parse JSON response; response.json() is Any at runtime so keep raw first
            if response.content:
                data_raw = response.json()
        except ValueError:
            data_raw = {}

        # Normalize to a mapping of str -> Any so static type checkers know 'data' is a dict
        if isinstance(data_raw, dict):
            data: Dict[str, Any] = cast(Dict[str, Any], data_raw)
        else:
            # Wrap non-dict JSON values in a dict under 'detail' for consistent error handling
            data: Dict[str, Any] = {"detail": data_raw}

        if response.status_code == 200 or response.status_code == 201:
            return data

        error_message = data.get("detail", response.text or "Unknown error")

        if response.status_code == 400:
            raise ValidationError(error_message, response.status_code, data)
        elif response.status_code == 401:
            raise AuthenticationError(error_message, response.status_code, data)
        elif response.status_code == 403:
            raise APIKeyError(error_message, response.status_code, data)
        elif response.status_code == 404:
            raise ResourceNotFoundError(
                error_message, response.status_code, data
            )
        elif response.status_code == 429:
            raise RateLimitError(error_message, response.status_code, data)
        elif response.status_code >= 500:
            raise ServerError(error_message, response.status_code, data)
        else:
            raise ByteITError(error_message, response.status_code, data)

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            The JSON response data

        Raises:
            NetworkError: If network error occurs after retries
            Various ByteITError subclasses for API errors
        """
        url = self._build_url(path)

        # If caller didn't provide a timeout, use the default per-method timeout
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)

        try:
            response = self._session.request(method, url, **kwargs)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            # Single attempt only; wrap network errors
            raise NetworkError(f"Request failed: {str(e)}")

    def create_job(
        self,
        input_connector: InputConnector,
        output_connector: Optional[OutputConnector] = None,
        processing_options: Optional[Dict[str, Any]] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Job:
        """
        Create a new document processing job.

        Args:
            input_connector: Input connector providing file data
            output_connector: Output connector for result storage (default: ByteITStorageOutputConnector)
            processing_options: Optional processing configuration dict with keys:
                - ocr_model: OCR model to use
                - vlm_model: Vision-Language model to use
                - languages: List of languages to detect/process
                - page_range: Page range to process (e.g., "1-5", "all")
                - output_format: Output format (json, txt, md, html)
            timeout: Request timeout in seconds

        Returns:
            Job object with initial job information

        Raises:
            ValidationError: If processing_options contains unexpected fields
            APIKeyError: If API key is invalid
            NetworkError: If network error occurs

        Example:
            >>> from byteit import LocalFileInputConnector, ByteITStorageOutputConnector
            >>> input_conn = LocalFileInputConnector("document.pdf")
            >>> output_conn = ByteITStorageOutputConnector()
            >>> options = {"ocr_model": "tesseract", "languages": ["en", "de"]}
            >>> job = client.create_job(input_conn, output_conn, options)
        """
        # Use default output connector if not provided
        if output_connector is None:
            output_connector = ByteITStorageOutputConnector()

        # Validate processing options if provided
        if processing_options:
            validate_processing_options(processing_options)

        # Get file data from input connector
        filename, file_obj = input_connector.get_file_data()

        # Get file type from connector
        connector_config = input_connector.to_dict()
        file_type = connector_config.get("file_type", "unknown")

        # Extract output_format from processing_options or use default
        output_format = "txt"  # Default as per backend contract
        clean_processing_options = {}

        if processing_options:
            # Make a copy to avoid modifying the original
            clean_processing_options = processing_options.copy()
            # Extract output_format if present
            if "output_format" in clean_processing_options:
                output_format = clean_processing_options.pop("output_format")

        # Prepare request data matching backend contract:
        # - file: FileField (sent via files parameter)
        # - file_type: CharField
        # - output_format: CharField
        # - processing_options: JSONField (without output_format)
        data: Dict[str, Any] = {
            "file_type": file_type,
            "output_format": output_format,
            "processing_options": clean_processing_options,
        }

        # Prepare files for multipart upload
        files = {"file": (filename, file_obj)}

        try:
            response = self._request(
                "POST",
                f"{API_BASE}/{JOBS_PATH}/",
                files=files,
                data=data,
                timeout=timeout,
            )

            # Extract job from response
            job_data = response.get("document", {})
            return Job.from_dict(job_data)
        finally:
            # Close file if it was opened by the connector
            if hasattr(file_obj, "close"):
                file_obj.close()

    def get_job(self, job_id: str, timeout: int = DEFAULT_TIMEOUT) -> Job:
        """
        Get information about a specific job.

        Args:
            job_id: The ID of the job to retrieve

        Returns:
            Job object with current job status

        Raises:
            ResourceNotFoundError: If job doesn't exist
            APIKeyError: If API key is invalid

        Example:
            >>> job = client.get_job("job-123")
            >>> print(job.processing_status)
        """
        response = self._request(
            "GET", f"{API_BASE}/{JOBS_PATH}/{job_id}/", timeout=timeout
        )
        job_data = response.get("document", {})
        return Job.from_dict(job_data)

    def list_jobs(
        self, user_id: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT
    ) -> JobList:  # Update to not request user_id
        """
        List all jobs for the authenticated user.

        Args:
            user_id: Optional user ID to filter jobs (admin only)

        Returns:
            JobList object with list of jobs

        Example:
            >>> job_list = client.list_jobs()
            >>> for job in job_list.jobs:
            ...     print(f"{job.id}: {job.processing_status}")
        """
        params = {}
        if user_id:
            params["user_id"] = user_id

        response = self._request(
            "GET", f"{API_BASE}/{JOBS_PATH}/", params=params, timeout=timeout
        )

        jobs = [Job.from_dict(doc) for doc in response.get("documents", [])]
        return JobList(
            jobs=jobs,
            count=response.get("count", len(jobs)),
            detail=response.get("detail", ""),
        )

    def get_job_result(
        self,
        job_id: str,
        output_path: Optional[Union[str, Path]] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Union[bytes, str]:
        """
        Download the processed document result.

        Args:
            job_id: The ID of the job
            output_path: Optional path to save the result file

        Returns:
            The processed document content as bytes or path string if saved

        Raises:
            ResourceNotFoundError: If job doesn't exist
            JobProcessingError: If job is not completed

        Example:
            >>> result = client.get_job_result("job-123", "output.md")
            >>> # Or get bytes directly
            >>> content = client.get_job_result("job-123")
        """
        url = self._build_url(f"{API_BASE}/{JOBS_PATH}/{job_id}/result/")

        try:
            response = self._session.get(url, timeout=timeout)

            # Check if response is JSON (error or status)
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = self._handle_response(response)
                # Job not ready yet
                if not data.get("ready", False):
                    raise JobProcessingError(
                        f"Job is not ready yet. Status: {data.get('processing_status')}",
                        response.status_code,
                        data,
                    )

            response.raise_for_status()

            # Get the file content
            content = response.content

            # Save to file if path provided
            if output_path:
                output_path = Path(output_path)
                output_path.write_bytes(content)
                return str(output_path)

            return content

        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Failed to download result: {str(e)}")

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: int = 5,
        max_wait_time: int = 600,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Job:
        """
        Wait for a job to complete by polling.

        Args:
            job_id: The ID of the job to wait for
            poll_interval: Seconds between status checks (default: 5)
            max_wait_time: Maximum seconds to wait (default: 600)

        Returns:
            Job object when completed

        Raises:
            JobProcessingError: If job fails or times out

        Example:
            >>> job = client.create_job(file, "pdf")
            >>> completed_job = client.wait_for_job(job.id)
            >>> result = client.get_job_result(completed_job.id)
        """
        start_time = time.time()

        while True:
            job = self.get_job(job_id, timeout=timeout)

            if job.is_completed:
                return job

            if job.is_failed:
                raise JobProcessingError(
                    f"Job failed: {job.processing_error or 'Unknown error'}"
                )

            elapsed = time.time() - start_time
            if elapsed >= max_wait_time:
                raise JobProcessingError(
                    f"Job timed out after {max_wait_time} seconds. Status: {job.processing_status}"
                )

            time.sleep(poll_interval)

    def process_document(
        self,
        input_connector: InputConnector,
        output_connector: Optional[OutputConnector] = None,
        processing_options: Optional[Dict[str, Any]] = None,
        output_path: Optional[Union[str, Path]] = None,
        poll_interval: int = 5,
        max_wait_time: int = 600,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Union[bytes, str]:
        """
        Convenience method to create a job, wait for completion, and get result.

        Args:
            input_connector: Input connector providing file data
            output_connector: Output connector for result storage (default: ByteITStorageOutputConnector)
            processing_options: Optional processing configuration dict
            output_path: Optional path to save result
            poll_interval: Seconds between status checks (default: 5)
            max_wait_time: Maximum seconds to wait (default: 600)
            timeout: Request timeout in seconds

        Returns:
            The processed document content or path if saved

        Example:
            >>> from byteit import LocalFileInputConnector
            >>> input_conn = LocalFileInputConnector("doc.pdf")
            >>> result = client.process_document(input_conn, output_path="output.md")
            >>> print(f"Saved to: {result}")
        """
        # Create job
        job = self.create_job(
            input_connector, output_connector, processing_options, timeout
        )

        # Wait for completion (use provided timeout for polling/get requests)
        self.wait_for_job(job.id, poll_interval, max_wait_time, timeout)

        # Get result
        return self.get_job_result(job.id, output_path, timeout)

    def close(self):
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self):
        """Context manager entry."""

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        self.close()
        """Context manager exit."""
        self.close()
