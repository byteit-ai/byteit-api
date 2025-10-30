"""Main API client for ByteIT text extraction service."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast, Type
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def _get_csrf_token(self) -> str:
        """
        Get CSRF token from the server.

        Returns:
            CSRF token string
        """
        if self._csrf_token:
            return self._csrf_token

        try:
            # Make a GET request to get CSRF cookie
            response = self._session.get(f"{self.BASE_URL}/")
            # Extract CSRF token from cookies
            csrf_cookie = response.cookies.get(
                "csrftoken"
            ) or response.cookies.get("csrf_token")
            if csrf_cookie:
                self._csrf_token = csrf_cookie
                return csrf_cookie
        except Exception:
            pass

        # Fallback: try to get from a dedicated endpoint
        try:
            response = self._session.get(f"{self.BASE_URL}/csrf/")
            if response.status_code == 200:
                data = response.json()
                self._csrf_token = data.get("csrf_token")
                return self._csrf_token
        except Exception:
            pass

        return ""

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

        # Add CSRF token for POST requests
        if method.upper() == "POST":
            csrf_token = self._get_csrf_token()
            if csrf_token:
                headers = kwargs.get("headers", {})
                headers["X-CSRFToken"] = csrf_token
                kwargs["headers"] = headers

        try:
            response = self._session.request(method, url, **kwargs)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            # Single attempt only; wrap network errors
            raise NetworkError(f"Request failed: {str(e)}")

    def _create_single_job(
        self,
        input_connector: InputConnector,
        output_connector: Optional[OutputConnector] = None,
        processing_options: Optional[Dict[str, Any]] = None,
        nickname: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        retry_on_db_lock: bool = True,
        max_retries: int = 3,
    ) -> Job:
        """
        Internal method to create a single job.

        Args:
            input_connector: Input connector providing file data
            output_connector: Output connector for result storage
            processing_options: Optional processing configuration dict
            nickname: Optional nickname for the job
            timeout: Request timeout in seconds
            retry_on_db_lock: Whether to retry on database lock errors (for SQLite)
            max_retries: Maximum number of retries for database lock errors

        Returns:
            Job object with initial job information
        """
        # Use default output connector if not provided
        if output_connector is None:
            output_connector = ByteITStorageOutputConnector()

        # Validate processing options if provided
        if processing_options:
            validate_processing_options(processing_options)

        # Get connector configuration
        connector_config = input_connector.to_dict()
        connector_type = connector_config.get("type", "localfile")

        # Extract output_format from processing_options or use default
        output_format = "txt"  # Default as per backend contract
        clean_processing_options = {}

        if processing_options:
            # Make a copy to avoid modifying the original
            clean_processing_options = processing_options.copy()
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

        if output_type and output_type != "byteit_storage":
            # For S3 and other custom output connectors
            data["output_connector"] = (
                "s3" if output_type == "s3" else output_type
            )
            data["output_connection_data"] = json.dumps(output_config)
        else:
            # For default ByteIT storage, send empty output_connector
            data["output_connector"] = ""
            data["output_connection_data"] = ""

        # Handle different input connector types
        files = None
        file_obj = None

        if connector_type == "s3":
            # For S3 connector, send connection data (no file upload)
            filename, connection_data = input_connector.get_file_data()
            data["input_connection_data"] = json.dumps(connection_data)
        else:
            # For local file connector, upload the file
            filename, file_obj = input_connector.get_file_data()
            files = {"file": (filename, file_obj)}

        last_error = None
        try:
            for attempt in range(max_retries + 1):
                try:
                    response = self._request(
                        "POST",
                        f"{API_BASE}/{JOBS_PATH}/",
                        files=files,
                        data=data,
                        timeout=timeout,
                    )

                    # Extract job from response
                    job_data = response.get("document", {}) or response.get(
                        "job", {}
                    )
                    return Job.from_dict(job_data)

                except (ServerError, ValidationError) as e:
                    # Check if it's a database lock error
                    error_msg = str(e).lower()
                    is_db_lock = (
                        "database is locked" in error_msg
                        or "database locked" in error_msg
                    )

                    if (
                        retry_on_db_lock
                        and is_db_lock
                        and attempt < max_retries
                    ):
                        # Exponential backoff: 0.1s, 0.2s, 0.4s, etc.
                        wait_time = 0.1 * (2**attempt)
                        time.sleep(wait_time)
                        last_error = e

                        # For local file connectors, close and reopen file
                        if file_obj is not None:
                            if (
                                hasattr(file_obj, "close")
                                and not file_obj.closed
                            ):
                                file_obj.close()

                            # Reopen file for retry
                            filename, file_obj = input_connector.get_file_data()
                            files = {"file": (filename, file_obj)}

                        # For S3 connectors, just retry with same data
                        continue
                    else:
                        # Not a DB lock error, or out of retries
                        raise

            # If we get here, all retries failed
            if last_error:
                raise last_error

            raise RuntimeError("Unexpected: no error but no success either")

        finally:
            # Always close file at the very end, regardless of success or failure
            # (Only applicable for local file connectors)
            if file_obj is not None and hasattr(file_obj, "close"):
                if not file_obj.closed:
                    file_obj.close()

    def create_job(
        self,
        input_connector: Union[InputConnector, List[InputConnector]],
        output_connector: Optional[OutputConnector] = None,
        processing_options: Optional[Dict[str, Any]] = None,
        nickname: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_workers: int = 5,
    ) -> Union[Job, List[Job]]:
        """
        Create one or more document processing jobs.

        Args:
            input_connector: Single InputConnector or list of InputConnectors
            output_connector: Output connector for result storage (default: ByteITStorageOutputConnector)
            processing_options: Optional processing configuration dict with keys:
                - ocr_model: OCR model to use
                - vlm_model: Vision-Language model to use
                - languages: List of languages to detect/process
                - page_range: Page range to process (e.g., "1-5", "all")
                - output_format: Output format (json, txt, md, html)
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

        Examples:
            Single file:
            >>> from byteit.connectors import LocalFileInputConnector
            >>> input_conn = LocalFileInputConnector("document.pdf")
            >>> job = client.create_job(input_conn)

            Multiple files (async):
            >>> input_conns = [
            ...     LocalFileInputConnector("doc1.pdf"),
            ...     LocalFileInputConnector("doc2.pdf"),
            ...     LocalFileInputConnector("doc3.pdf")
            ... ]
            >>> jobs = client.create_job(input_conns)
            >>> print(f"Created {len(jobs)} jobs")

            Multiple files with SQLite backend (dev):
            >>> # Use max_workers=1 to avoid SQLite database lock errors
            >>> jobs = client.create_job(input_conns, max_workers=1)
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

        # Handle list of connectors - process asynchronously
        if not isinstance(input_connector, list):
            raise TypeError(
                "input_connector must be an InputConnector or a list of InputConnectors"
            )

        if not input_connector:
            raise ValueError("input_connector list cannot be empty")

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
                except Exception as e:
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

    def _create_single_job(
        self,
        input_connector: InputConnector,
        output_connector: Optional[OutputConnector],
        processing_options: Optional[Dict[str, Any]],
        nickname: Optional[str],
        timeout: int,
    ) -> Job:
        """
        Create a single job.

        Args:
            input_connector: Input connector
            output_connector: Output connector
            processing_options: Processing options
            nickname: Job nickname
            timeout: Request timeout

        Returns:
            Job object
        """

        # Get input connector info
        input_config = input_connector.to_dict()
        input_type = input_config.get("type")

        # Build request data
        data = {
            "input_connector": input_type,
        }

        # Add input connection data for S3
        if input_type == "s3":
            _, connection_data = input_connector.get_file_data()
            data["input_connection_data"] = json.dumps(connection_data)
        # For local files, no input_connection_data (file would be uploaded separately)

        # Add output connector
        if output_connector:
            output_config = output_connector.to_dict()

            data["output_connector"] = "s3"
            data["output_connection_data"] = json.dumps(output_config)
        else:
            data["output_connector"] = ""
            data["output_connection_data"] = ""

        # Add processing options
        if processing_options:
            # Extract output_format if present
            output_format = processing_options.get("output_format")
            if output_format:
                data["output_format"] = output_format
                # Remove from processing_options
                clean_options = processing_options.copy()
                clean_options.pop("output_format", None)
                if clean_options:
                    data["processing_options"] = json.dumps(clean_options)
            else:
                data["processing_options"] = json.dumps(processing_options)

        # Add nickname
        if nickname:
            data["nickname"] = nickname

        response = self._request(
            "POST", f"{API_BASE}/{JOBS_PATH}/", data=data, timeout=timeout
        )
        job_data = response.get("job", response.get("document", response))
        return Job.from_dict(job_data)

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

        job_data = response.get("job", response.get("document", response))
        return Job.from_dict(job_data)

    def list_jobs(
        self, timeout: int = DEFAULT_TIMEOUT
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

            # First check the status code
            response.raise_for_status()

            # Check if this is a file download by looking for Content-Disposition header
            content_disposition = response.headers.get(
                "Content-Disposition", ""
            )
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
        input_connector: Union[InputConnector, List[InputConnector]],
        output_connector: Optional[OutputConnector] = None,
        processing_options: Optional[Dict[str, Any]] = None,
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
            processing_options: Optional processing configuration dict
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

        Examples:
            Single file:
            >>> from byteit.connectors import LocalFileInputConnector
            >>> input_conn = LocalFileInputConnector("doc.pdf")
            >>> result = client.process_document(input_conn, output_path="output.md")
            >>> print(f"Saved to: {result}")

            Multiple files:
            >>> input_conns = [
            ...     LocalFileInputConnector("doc1.pdf"),
            ...     LocalFileInputConnector("doc2.pdf")
            ... ]
            >>> output_paths = ["output1.txt", "output2.txt"]
            >>> results = client.process_document(input_conns, output_path=output_paths)
            >>> print(f"Processed {len(results)} documents")
        """
        # Handle single connector
        if isinstance(input_connector, InputConnector):
            # Create job
            job = self.create_job(
                input_connector,
                output_connector,
                processing_options,
                nickname,
                timeout,
            )

            # Wait for completion
            self.wait_for_job(job.id, poll_interval, max_wait_time, timeout)

            # Get result
            single_output_path = (
                output_path if not isinstance(output_path, list) else None
            )
            return self.get_job_result(job.id, single_output_path, timeout)

        # Handle list of connectors
        if not isinstance(input_connector, list):
            raise TypeError(
                "input_connector must be an InputConnector or a list of InputConnectors"
            )

        if not input_connector:
            raise ValueError("input_connector list cannot be empty")

        # Validate output_path if provided
        if output_path is not None and isinstance(output_path, list):
            if len(output_path) != len(input_connector):
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

        # Wait for all jobs to complete and get results concurrently
        results: List[Union[bytes, str]] = []
        errors: List[tuple[int, Exception]] = []

        def process_single_job(
            idx: int, job: Job
        ) -> tuple[int, Union[bytes, str]]:
            """Process a single job: wait and get result."""
            # Wait for completion
            self.wait_for_job(job.id, poll_interval, max_wait_time, timeout)

            # Determine output path for this job
            job_output_path = None
            if output_path is not None:
                if isinstance(output_path, list):
                    job_output_path = output_path[idx]
                else:
                    # Single path provided for multiple files - create numbered paths
                    path = Path(output_path)
                    job_output_path = (
                        path.parent / f"{path.stem}_{idx}{path.suffix}"
                    )

            # Get result
            result = self.get_job_result(job.id, job_output_path, timeout)
            return (idx, result)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all job processing tasks
            future_to_index = {
                executor.submit(process_single_job, idx, job): idx
                for idx, job in enumerate(jobs)
            }

            # Collect results
            result_map: Dict[int, Union[bytes, str]] = {}
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result_idx, result = future.result()
                    result_map[result_idx] = result
                except Exception as e:
                    errors.append((idx, e))

        # Sort results by original index
        results = [result_map[idx] for idx in sorted(result_map.keys())]

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
