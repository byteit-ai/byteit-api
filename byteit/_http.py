"""HTTP request helpers and URL builders for the ByteIT API client."""

from typing import Any
from urllib.parse import quote

import requests

from .exceptions import (
    APIKeyError,
    AuthenticationError,
    ByteITError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)

API_VERSION = "v1"
API_BASE = f"/{API_VERSION}"
JOBS_PATH = "jobs"
PARSE_JOBS_PATH = "parse-jobs"
EXTRACT_JOBS_PATH = "extract-jobs"
CLASSIFICATION_JOBS_PATH = "classification-jobs"
SCHEMAS_PATH = "schemas"
FILE_CLASSES_PATH = "file-classes"
USER_FILE_CLASSES_PATH = "user-file-classes"
CUSTOM_JOBS_PATH = "custom-jobs"


def build_url(base_url: str, path: str) -> str:
    """Build full URL from base and path."""
    return f"{base_url}/{path.lstrip('/')}"


def build_job_collection_path(job_type: str | None = None) -> str:
    """Build a collection path under the jobs API namespace."""
    segments = [API_BASE, JOBS_PATH]
    if job_type:
        segments.append(job_type)
    return "/" + "/".join(segment.strip("/") for segment in segments) + "/"


def build_job_resource_path(job_id: str, job_type: str | None = None) -> str:
    """Build a resource path for a specific job type."""
    return f"{build_job_collection_path(job_type)}{job_id}/"


def build_job_result_path(job_id: str, job_type: str | None = None) -> str:
    """Build a result download path for a specific job type."""
    return f"{build_job_resource_path(job_id, job_type)}result/"


def build_job_status_path(job_id: str) -> str:
    """Build the generic jobs processing-status path."""
    return f"{build_job_resource_path(job_id)}status/"


def build_schema_collection_path() -> str:
    """Build the saved-schema collection path."""
    segments = [API_BASE, SCHEMAS_PATH]
    return "/" + "/".join(segment.strip("/") for segment in segments) + "/"


def build_schema_resource_path(name: str) -> str:
    """Build the saved-schema resource path for a schema name."""
    normalized_name = _normalize_schema_name(name)
    encoded_name = quote(normalized_name, safe="")
    return f"{build_schema_collection_path()}{encoded_name}/"


def build_file_class_collection_path() -> str:
    """Build the system default file-class collection path."""
    segments = [API_BASE, FILE_CLASSES_PATH]
    return "/" + "/".join(segment.strip("/") for segment in segments) + "/"


def build_user_file_class_collection_path() -> str:
    """Build the user-owned file-class collection path."""
    segments = [API_BASE, USER_FILE_CLASSES_PATH]
    return "/" + "/".join(segment.strip("/") for segment in segments) + "/"


def build_user_file_class_resource_path(label: str) -> str:
    """Build the user file-class resource path for a label."""
    normalized_label = _normalize_file_class_label(label)
    encoded_label = quote(normalized_label, safe="")
    return f"{build_user_file_class_collection_path()}{encoded_label}/"


def extract_job_data(
    response: dict[str, Any],
    primary_key: str,
) -> dict[str, Any]:
    """Extract a job payload from known API response shapes."""
    return response.get(
        primary_key,
        response.get("job", response.get("document", response)),
    )


def _normalize_schema_name(name: str) -> str:
    """Normalize a saved-schema name before sending it to the API."""
    if not isinstance(name, str):
        raise ValidationError("name must be a non-empty string")

    normalized_name = name.strip()
    if not normalized_name:
        raise ValidationError("name must be a non-empty string")

    return normalized_name


def _normalize_file_class_label(label: str) -> str:
    """Normalize a file-class label before sending it to the API."""
    if not isinstance(label, str):
        raise ValidationError("label must be a non-empty string")

    normalized_label = label.strip()
    if not normalized_label:
        raise ValidationError("label must be a non-empty string")

    return normalized_label


def is_duplicate_saved_schema_error(error: ValidationError) -> bool:
    """Return True when a validation error represents duplicate saved-schema name."""
    if error.status_code != 400:
        return False

    error_message = (error.message or "").lower()
    return "schema" in error_message and "already exists" in error_message


def parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header value into seconds."""
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def extract_error_message(
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


def handle_response(response: requests.Response) -> dict[str, Any]:
    """Handle API response and raise appropriate exceptions."""
    if response.status_code in (200, 201, 204):
        return response.json() if response.content else {}

    try:
        data: dict[str, Any] = response.json() if response.content else {}
        message: str = (
            data.get("detail", "")
            or data.get("error", "")
            or response.text
            or "Request failed"
        )
    except (ValueError, requests.exceptions.JSONDecodeError):
        data = {}
        message = extract_error_message(data, response)

    if response.status_code == 429:
        retry_after = parse_retry_after(response.headers.get("Retry-After"))
        raise RateLimitError(
            message,
            response.status_code,
            data,
            retry_after_seconds=retry_after,
        )

    error_map: dict[int, type[Exception]] = {
        400: ValidationError,
        401: AuthenticationError,
        403: APIKeyError,
        404: ResourceNotFoundError,
    }

    exc_class = error_map.get(response.status_code)
    if exc_class:
        raise exc_class(message, response.status_code, data)

    if response.status_code >= 500:
        raise ServerError(message, response.status_code, data)

    raise ByteITError(message, response.status_code, data)
