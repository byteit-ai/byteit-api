"""ByteIT Python Client Library for text extraction."""

from .api_client import ByteITClient
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
from .models.DocumentMetadata import DocumentMetadata
from .connectors import (
    InputConnector,
    OutputConnector,
    LocalFileInputConnector,
    ByteITStorageOutputConnector,
)
from .validations import validate_processing_options

__version__ = "0.1.0"

__all__ = [
    "ByteITClient",
    "Job",
    "JobList",
    "DocumentMetadata",
    "InputConnector",
    "OutputConnector",
    "LocalFileInputConnector",
    "ByteITStorageOutputConnector",
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
