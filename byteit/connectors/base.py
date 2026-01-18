"""Base classes for ByteIT connectors."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class InputConnector(ABC):
    """Abstract base for input data sources.

    Input connectors define how ByteIT accesses documents for processing.
    Implementations handle local files, S3 buckets, and other data sources.

    Subclasses must implement:
        - get_file_data(): Returns file data for upload or connection info
        - to_dict(): Serializes connector configuration for API
    """

    @abstractmethod
    def get_file_data(self) -> Tuple[str, Any]:
        """
        Get file data for upload.

        Returns:
            Tuple of (filename, file_object) suitable for requests.files
        """
        ...

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert connector configuration to dictionary for API submission.

        Returns:
            Dictionary representation of the connector configuration
        """
        ...


class OutputConnector(ABC):
    """Abstract base for output destinations.

    Output connectors define where ByteIT stores processed results.
    Implementations handle local storage, S3 buckets, and other destinations.

    Subclasses must implement:
        - to_dict(): Serializes connector configuration for API
    """

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert connector configuration to dictionary for API submission.

        Returns:
            Dictionary representation of the connector configuration
        """
        ...
