"""Connector classes for ByteIT file input and output operations."""

from .base import InputConnector, OutputConnector
from .LocalFileInputConnector import LocalFileInputConnector
from .LocalFileOutputConnector import LocalFileOutputConnector

# S3 connectors are optional and require boto3
try:
    from .S3InputConnector import S3InputConnector
    from .S3OutputConnector import S3OutputConnector

    _s3_available = True
except ImportError:
    _s3_available = False
    S3InputConnector = None  # type: ignore
    S3OutputConnector = None  # type: ignore

__all__ = [
    "InputConnector",
    "OutputConnector",
    "LocalFileInputConnector",
    "LocalFileOutputConnector",
]

if _s3_available:
    __all__.extend(["S3InputConnector", "S3OutputConnector"])
