"""Base classes for ByteIT connectors."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class InputConnector(ABC):
    """Base class for input connectors that provide file data to ByteIT."""

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
    """Base class for output connectors that handle processed results."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert connector configuration to dictionary for API submission.

        Returns:
            Dictionary representation of the connector configuration
        """
        ...
