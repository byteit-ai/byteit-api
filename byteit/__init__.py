"""ByteIT Python Client Library for text extraction."""

from .ByteITClient import ByteITClient
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
from .models.ProcessingOptions import ProcessingOptions
from .models.OutputFormat import OutputFormat
from .connectors import (
    InputConnector,
    OutputConnector,
    LocalFileInputConnector,
    LocalFileOutputConnector,
)
from .validations import validate_processing_options

__version__ = "0.1.0"

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
