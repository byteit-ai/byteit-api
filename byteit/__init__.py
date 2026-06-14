"""ByteIT Python Client Library for text extraction."""

import os
import sys
import warnings

import requests

from .ByteITClient import ByteITClient
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
    NetworkError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)
from .models.DocumentMetadata import DocumentMetadata
from .models.ExtractionType import ExtractionType
from .models.ExtractJob import ExtractJob
from .models.ExtractJobList import ExtractJobList
from .models.JobList import JobList
from .models.JobStatus import JobStatus
from .models.OutputFormat import OutputFormat
from .models.ParseJob import ParseJob
from .models.ProcessingOptions import ProcessingOptions
from .models.SavedSchema import SavedSchema
from .models.SavedSchemaList import SavedSchemaList
from .validations import validate_processing_options

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    # For Python <3.8
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

try:
    __version__ = version("byteit")
except PackageNotFoundError:
    __version__ = "1.1.2"  # fallback, keep in sync with pyproject.toml

try:
    from .models.ExtractionSchema import ExtractionSchema  # noqa: F401

    __all_extraction_schema__ = ["ExtractionSchema"]
except ImportError:
    __all_extraction_schema__ = []

_PYPI_VERSION_URL = "https://pypi.org/pypi/byteit/json"
_VERSION_CHECK_TIMEOUT_SECONDS = 2


def _should_check_latest_version() -> bool:
    """Return True when the import-time version check should run."""
    disabled_value = os.getenv("BYTEIT_DISABLE_VERSION_CHECK", "").strip().lower()
    if disabled_value in {"1", "true", "yes", "on"}:
        return False

    # Avoid noisy network access during tests and CI.
    return not ("pytest" in sys.modules or os.getenv("CI"))


def _check_latest_version() -> None:
    """Warn when the current runtime version differs from the PyPI release."""
    if not _should_check_latest_version():
        return

    try:
        response = requests.get(_PYPI_VERSION_URL, timeout=_VERSION_CHECK_TIMEOUT_SECONDS)
        response.raise_for_status()
        pypi_version = response.json().get("info", {}).get("version")
        if not pypi_version or pypi_version == __version__:
            return
    except Exception:
        return

    warnings.warn(
        "byteit version mismatch: local version is "
        f"{__version__}, published PyPI version is {pypi_version}. "
        "Run 'pip install --upgrade byteit' to sync with the published release.",
        UserWarning,
        stacklevel=2,
    )


__all__ = [
    "ByteITClient",
    "JobList",
    "JobStatus",
    "DocumentMetadata",
    "ProcessingOptions",
    "ExtractionType",
    "ExtractJob",
    "ExtractJobList",
    "OutputFormat",
    "ParseJob",
    "InputConnector",
    "OutputConnector",
    "LocalFileInputConnector",
    "LocalFileOutputConnector",
    "SavedSchema",
    "SavedSchemaList",
    "validate_processing_options",
    "ByteITError",
    "AuthenticationError",
    "APIKeyError",
    "ValidationError",
    "ResourceNotFoundError",
    "RateLimitError",
    "ServerError",
    "NetworkError",
    "JobProcessingError",
    *__all_extraction_schema__,
]

_check_latest_version()
