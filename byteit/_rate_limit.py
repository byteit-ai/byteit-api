"""Rate-limit-aware submission helpers."""

import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from ._http import PARSE_JOBS_PATH, build_job_collection_path, build_url, handle_response
from .connectors import InputConnector
from .exceptions import RateLimitError


class RateLimitedSubmitter:
    """Manages parse-job submissions with adaptive rate-limit handling.

    Wraps submission pacing, backoff, and per-file uploads into a single
    stateful helper attached to the client's session.
    """

    def __init__(
        self,
        session: Any,
        base_url: str,
        default_timeout: float,
        rate_limit_max_retries: int,
        rate_limit_base_delay: float,
        rate_limit_max_delay: float,
    ) -> None:
        self._session = session
        self._base_url = base_url
        self._default_timeout = default_timeout
        self._rate_limit_max_retries = rate_limit_max_retries
        self._rate_limit_base_delay = rate_limit_base_delay
        self._rate_limit_max_delay = rate_limit_max_delay
        self._submission_delay = 0.0
        self._last_submission_at: float | None = None

    def wait_before_submission(self) -> None:
        """Sleep when a previous rate limit requires spacing between submissions."""
        if self._submission_delay <= 0 or self._last_submission_at is None:
            return

        elapsed = time.monotonic() - self._last_submission_at
        wait_time = self._submission_delay - elapsed
        if wait_time > 0:
            time.sleep(wait_time)

    def record_successful_submission(self) -> None:
        """Track submission timing and gradually reduce adaptive throttling."""
        self._last_submission_at = time.monotonic()
        if self._submission_delay > self._rate_limit_base_delay:
            self._submission_delay = max(
                self._rate_limit_base_delay,
                self._submission_delay * 0.5,
            )

    def backoff_after_rate_limit(self, error: RateLimitError) -> float:
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

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make HTTP request via the session."""
        url = build_url(self._base_url, path)
        kwargs.setdefault("timeout", self._default_timeout)
        response = self._session.request(method, url, **kwargs)
        return handle_response(response)

    def submit_parse_job_request(
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

                self.wait_before_submission()
                response = self._request(
                    "POST",
                    build_job_collection_path(PARSE_JOBS_PATH),
                    files=request_files,
                    data=data,
                )
                self.record_successful_submission()
                return response
            except RateLimitError as exc:
                if attempt >= self._rate_limit_max_retries:
                    raise
                delay = self.backoff_after_rate_limit(exc)
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

    def submit_multi_file_batch(
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

                    self.wait_before_submission()
                    response = self._request(
                        "POST",
                        build_job_collection_path(PARSE_JOBS_PATH),
                        files=request_files,
                        data=data,
                    )
                self.record_successful_submission()
                return response
            except RateLimitError as exc:
                if attempt >= self._rate_limit_max_retries:
                    raise
                delay = self.backoff_after_rate_limit(exc)
                print(
                    "Rate limited. Waiting "
                    f"{delay:.1f}s before retry "
                    f"({attempt + 1}/{self._rate_limit_max_retries})..."
                )
                time.sleep(delay)

        raise RateLimitError("Rate limit exceeded after retries.", status_code=429)
