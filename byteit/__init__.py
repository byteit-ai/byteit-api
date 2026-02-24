"""ByteIT Python Client Library for text extraction."""

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
from .models.Job import Job
from .models.JobList import JobList
from .models.OutputFormat import OutputFormat
from .models.ProcessingOptions import ProcessingOptions
from .validations import validate_processing_options

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    # For Python <3.8
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

try:
    __version__ = version("byteit")
except PackageNotFoundError:
    __version__ = "0.1.2"  # fallback, keep in sync with pyproject.toml

__all__ = [
    "ByteITClient",
    "Job",
    "JobList",
    "DocumentMetadata",
    "ProcessingOptions",
    "OutputFormat",
    "InputConnector",
    "OutputConnector",
    "LocalFileInputConnector",
    "LocalFileOutputConnector",
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
]
