"""Main API client for ByteIT text extraction service."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Optional, Type, Union, cast

import requests

from .connectors import (
    ByteITStorageOutputConnector,
    InputConnector,
    OutputConnector,
)
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
from .models.Job import Job
from .models.JobList import JobList
from .models.ProcessingOptions import ProcessingOptions

# API path constants so endpoints can be changed in one place
API_VERSION = "v1"
API_BASE = f"/{API_VERSION}"
JOBS_PATH = "jobs"


class ByteITClient:
    """
    Client for interacting with the ByteIT text extraction API.
    """

    # BASE_URL = "https://api.byteit.ai"
    BASE_URL = "http://127.0.0.1:8000"
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
        self._csrf_token = None

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

        data_raw: Any = {}
        try:
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

        response = self._session.request(method, url, **kwargs)
        return self._handle_response(response)

    def _create_single_job(
        self,
        input_connector: InputConnector,
        output_connector: Optional[OutputConnector] = None,
        processing_options: Optional[ProcessingOptions] = None,
        nickname: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Job:
        """
        Internal method to create a single job.

        Args:
            input_connector: Input connector providing file data
            output_connector: Output connector for result storage
            processing_options: Optional processing configuration (ProcessingOptions object)
            nickname: Optional nickname for the job
            timeout: Request timeout in seconds

        Returns:
            Job object with initial job information
        """
        # Use default output connector if not provided
        if output_connector is None:
            output_connector = ByteITStorageOutputConnector()

        # Convert ProcessingOptions to dict if provided
        options_dict: Optional[Dict[str, Any]] = None
        if processing_options is not None:
            options_dict = processing_options.to_dict()

        # Get connector configuration
        connector_config = input_connector.to_dict()
        connector_type = (
            connector_config.get("type", "localfile").strip().lower()
        )

        # Extract output_format from processing_options or use default
        output_format = "txt"
        clean_processing_options: Dict[str, Any] = {}

        if options_dict:
            # Make a copy to avoid modifying the original
            clean_processing_options = options_dict.copy()
            # Extract output_format if present
            if "output_format" in clean_processing_options:
                output_format = clean_processing_options.pop("output_format")

        # Prepare request data matching backend contract
        data: Dict[str, Any] = {
            "output_format": output_format,
            "processing_options": json.dumps(clean_processing_options),
            "input_connector": connector_type,
        }

        # Add nickname if provided
        if nickname:
            data["nickname"] = nickname

        # Add output connector configuration
        output_config = output_connector.to_dict()
        output_type = output_config.get("type")

        if output_type:
            data["output_connector"] = output_type
            data["output_connection_data"] = json.dumps(output_config)
        else:
            # For default ByteIT storage, send empty output_connector
            data["output_connector"] = ""
            data["output_connection_data"] = "{}"

        # Handle different input connector types
        files = None
        file_obj = None

        # TODO: This needs to be updated once we add more connectors
        if connector_type == "localfile":
            # For local file connector, upload the file
            filename, file_obj = input_connector.get_file_data()
            files = {"file": (filename, file_obj)}
        elif connector_type == "s3":
            # For S3 connector, send connection data (no file upload)
            filename, connection_data = input_connector.get_file_data()
            data["input_connection_data"] = json.dumps(connection_data)
        else:
            raise ValidationError(
                f"Unsupported input connector type: {connector_type}"
            )

        response = self._request(
            "POST",
            f"{API_BASE}/{JOBS_PATH}/",
            files=files,
            data=data,
            timeout=timeout,
        )

        # Close file object after request is done
        if file_obj is not None and hasattr(file_obj, "close"):
            if not file_obj.closed:
                file_obj.close()

        # Extract job from response
        job_data = response.get("document", {}) or response.get("job", {})
        return Job.from_dict(job_data)

    def create_job(
        self,
        input_connector: Union[InputConnector, List[InputConnector]],
        output_connector: Optional[OutputConnector] = None,
        processing_options: Optional[ProcessingOptions] = None,
        nickname: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_workers: int = 5,
    ) -> Union[Job, List[Job]]:
        """
        Create one or more document processing jobs.

        Args:
            input_connector: Single InputConnector or list of InputConnectors
            output_connector: Output connector for result storage (default: ByteITStorageOutputConnector)
            processing_options: Optional processing configuration (ProcessingOptions object) with fields:
                - ocr_model: OCR model to use
                - languages: List of languages to detect/process
                - page_range: Page range to process (e.g., "1-5", "all")
                - output_format: Output format (txt, json, md, html)
            nickname: Optional nickname for the job (for easier identification)
            timeout: Request timeout in seconds
            max_workers: Maximum number of concurrent workers for batch processing (default: 5)
                Note: When using SQLite backend (dev), set to 1 to avoid database lock issues.
                Production PostgreSQL databases handle concurrent requests without issues.

        Returns:
            Single Job object if single connector provided, or List[Job] if list provided.
            Jobs are created asynchronously when multiple connectors are provided.

        Raises:
            ValidationError: If processing_options contains unexpected fields
            APIKeyError: If API key is invalid
            NetworkError: If network error occurs
            JobProcessingError: If any job creation fails
        """
        # Handle single connector
        if isinstance(input_connector, InputConnector):
            return self._create_single_job(
                input_connector,
                output_connector,
                processing_options,
                nickname,
                timeout,
            )

        if not input_connector:
            raise ValueError("input_connector list cannot be empty")

        # At this point we know a list of input connectors was given
        # Process multiple files concurrently using ThreadPoolExecutor
        jobs: List[Job] = []
        errors: List[tuple[int, Exception]] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_index = {
                executor.submit(
                    self._create_single_job,
                    conn,
                    output_connector,
                    processing_options,
                    nickname,
                    timeout,
                ): idx
                for idx, conn in enumerate(input_connector)
            }

            # Collect results as they complete
            job_results: Dict[int, Job] = {}
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    job = future.result()
                    job_results[idx] = job
                except (
                    Exception
                ) as e:  # .result raises Exception and therefore this is needed.
                    errors.append((idx, e))

        # Sort jobs by original index to maintain order
        jobs = [job_results[idx] for idx in sorted(job_results.keys())]

        # Raise exception if any jobs failed
        if errors:
            error_msg = f"Failed to create {len(errors)} job(s):\n"
            for idx, error in errors:
                error_msg += f"  - File {idx}: {str(error)}\n"
            raise JobProcessingError(error_msg)

        return jobs

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
        """
        response = self._request(
            "GET", f"{API_BASE}/{JOBS_PATH}/{job_id}/", timeout=timeout
        )

        job_data = response.get("job", response.get("document", response))
        return Job.from_dict(job_data)

    def list_jobs(self, timeout: int = DEFAULT_TIMEOUT) -> JobList:
        """
        List all jobs for the authenticated user.

        Args:
            user_id: Optional user ID to filter jobs (admin only)

        Returns:
            JobList object with list of jobs
        """
        params = {}

        response = self._request(
            "GET", f"{API_BASE}/{JOBS_PATH}/", params=params, timeout=timeout
        )

        jobs_data = response.get("jobs", response.get("documents", []))
        jobs = [Job.from_dict(doc) for doc in jobs_data]
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
        """
        url = self._build_url(f"{API_BASE}/{JOBS_PATH}/{job_id}/result/")

        response = self._session.get(url, timeout=timeout)

        # First check the status code
        response.raise_for_status()

        # Check if this is a file download by looking for Content-Disposition header
        content_disposition = response.headers.get("Content-Disposition", "")
        content_type = response.headers.get("Content-Type", "")

        # If Content-Disposition is present with "attachment", it's a file download
        # This is true even if Content-Type is application/json (for JSON result files)
        if "attachment" in content_disposition:
            # This is a file download (the actual result)
            content = response.content

            # Save to file if path provided
            if output_path:
                output_path = Path(output_path)
                output_path.write_bytes(content)
                return str(output_path)

            return content

        # If no Content-Disposition with attachment, check if it's a JSON status response
        if "application/json" in content_type:
            # This means the job is not ready or there's an error
            data = self._handle_response(response)
            # Job not ready yet
            if not data.get("ready", False):
                raise JobProcessingError(
                    f"Job is not ready yet. Status: {data.get('processing_status')}",
                    response.status_code,
                    data,
                )
            # If we get here with JSON, something unexpected happened
            raise JobProcessingError(
                f"Unexpected JSON response: {data}",
                response.status_code,
                data,
            )

        # If we get here, it's a file response (not JSON)
        # Get the file content
        content = response.content

        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.write_bytes(content)
            return str(output_path)

        return content

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
            poll_interval: Sectheonds between status checks (default: 5)
            max_wait_time: Maximum seconds to wait (default: 600)

        Returns:
            Job object when completed

        Raises:
            JobProcessingError: If job fails or times out
        """
        start_time = time.time()

        while True:
            job = self.get_job(job_id, timeout=timeout)

            if job.is_completed:
                return job

            if job.is_failed:
                raise JobProcessingError(
                    f"Job failtheed: {job.processing_error or 'Unknown error'}"
                )

            elapsed = time.time() - start_time
            if elapsed >= max_wait_time:
                raise JobProcessingError(
                    f"Job timed out after {max_wait_time} seconds. Status: {job.processing_status}"
                )

            time.sleep(poll_interval)

    def process_document(
        self,
        input_connector: Union[InputConnector, List[InputConnector]],
        output_connector: Optional[OutputConnector] = None,
        processing_options: Optional[ProcessingOptions] = None,
        nickname: Optional[str] = None,
        output_path: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
        poll_interval: int = 5,
        max_wait_time: int = 600,
        timeout: int = DEFAULT_TIMEOUT,
        max_workers: int = 5,
    ) -> Union[bytes, str, List[Union[bytes, str]]]:
        """
        Convenience method to create job(s), wait for completion, and get result(s).

        Args:
            input_connector: Single InputConnector or list of InputConnectors
            output_connector: Output connector for result storage (default: ByteITStorageOutputConnector)
            processing_options: Optional processing configuration (ProcessingOptions object)
            nickname: Optional nickname for the job (for easier identification)
            output_path: Optional path(s) to save result(s). Can be:
                - Single path (str/Path) when processing one file
                - List of paths when processing multiple files
                - None to return content without saving
            poll_interval: Seconds between status checks (default: 5)
            max_wait_time: Maximum seconds to wait (default: 600)
            timeout: Request timeout in seconds
            max_workers: Maximum concurrent workers for batch processing (default: 5)

        Returns:
            Single result (bytes or str) if single connector provided,
            or List[bytes | str] if list of connectors provided
        """
        # Handle single connector
        if isinstance(input_connector, InputConnector):
            # Create job
            job_result = self.create_job(
                input_connector,
                output_connector,
                processing_options,
                nickname,
                timeout,
            )

            # Type narrowing: we know it's a single Job
            if not isinstance(job_result, Job):
                raise RuntimeError("Expected single Job from create_job")

            # Wait for completion
            self.wait_for_job(
                job_result.id, poll_interval, max_wait_time, timeout
            )

            # Get result
            single_output_path = (
                output_path if not isinstance(output_path, list) else None
            )
            return self.get_job_result(
                job_result.id, single_output_path, timeout
            )

        # Handle list of connectors
        if not input_connector:
            raise ValueError("input_connector list cannot be empty")

        # Validate output_path if provided
        if isinstance(output_path, list) and len(output_path) != len(
            input_connector
        ):
            raise ValueError(
                f"output_path list length ({len(output_path)}) must match "
                f"input_connector list length ({len(input_connector)})"
            )

        # Create all jobs asynchronously
        jobs = self.create_job(
            input_connector,
            output_connector,
            processing_options,
            nickname,
            timeout,
            max_workers,
        )

        if not isinstance(jobs, list):
            raise RuntimeError("Expected list of jobs from create_job")

        # Wait for all jobs to complete and get results
        results: List[Union[bytes, str]] = []
        errors: List[tuple[int, Exception]] = []

        for idx, job in enumerate(jobs):
            # Determine output path for this job
            job_output_path = None
            if output_path is not None:
                if isinstance(output_path, list):
                    job_output_path = output_path[idx]
                else:
                    path = Path(output_path)
                    job_output_path = (
                        path.parent / f"{path.stem}_{idx}{path.suffix}"
                    )

            try:
                # Wait for completion
                self.wait_for_job(job.id, poll_interval, max_wait_time, timeout)

                # Get result
                result = self.get_job_result(job.id, job_output_path, timeout)
                results.append(result)
            except (JobProcessingError, NetworkError) as e:
                errors.append((idx, e))

        # Raise exception if any processing failed
        if errors:
            error_msg = f"Failed to process {len(errors)} document(s):\n"
            for idx, error in errors:
                error_msg += f"  - Document {idx}: {str(error)}\n"
            raise JobProcessingError(error_msg)

        return results

    def close(self):
        """Close the HTTP session."""
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
