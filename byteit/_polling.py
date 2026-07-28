"""Adaptive polling helpers for job completion."""

import dataclasses
import time
from collections.abc import Callable
from typing import Any

from .exceptions import JobProcessingError
from .models.CustomJob import CustomJob
from .models.ExtractJob import ExtractJob
from .models.JobStatus import JobStatus
from .models.ParseJob import ParseJob
from .progress import ProgressTracker


def poll_until(
    get_status: Callable[[str], dict[str, Any] | JobStatus],
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
        status = get_status(job_id)
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


def wait_for_completion(
    get_status: Callable[[str], dict[str, Any] | JobStatus],
    job_id: str,
    input_connector: Any | None = None,
    job: ParseJob | None = None,
) -> ParseJob:
    """Wait for a parse job to complete with adaptive polling."""
    tracker = ProgressTracker(input_connector)
    initial_status = job

    def _update(j: ParseJob | None, s: JobStatus) -> ParseJob:
        return _merge_job_status(job_id, s, j)

    return poll_until(
        get_status,
        job_id,
        initial_status,
        _update,
        error_prefix="Job",
        tracker=tracker,
    )


def wait_for_extract_completion(
    get_status: Callable[[str], dict[str, Any] | JobStatus],
    job_id: str,
    job: ExtractJob,
) -> ExtractJob:
    """Wait for an extraction job to complete with adaptive polling."""

    def _update(j: ExtractJob, s: JobStatus) -> ExtractJob:
        return dataclasses.replace(
            j,
            processing_status=s.processing_status,
        )

    return poll_until(
        get_status,
        job_id,
        job,
        _update,
        error_prefix="Extraction job",
    )


def wait_for_custom_job_completion(
    get_status: Callable[[str], dict[str, Any] | JobStatus],
    job_id: str,
    job: CustomJob,
) -> CustomJob:
    """Wait for a custom job to complete with adaptive polling."""

    def _update(j: CustomJob, s: JobStatus) -> CustomJob:
        return dataclasses.replace(j, processing_status=s.processing_status)

    return poll_until(
        get_status,
        job_id,
        job,
        _update,
        error_prefix="Custom job",
    )


def _merge_job_status(
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

    return dataclasses.replace(
        job,
        processing_status=status.processing_status,
        processing_error=status.message or job.processing_error,
    )
