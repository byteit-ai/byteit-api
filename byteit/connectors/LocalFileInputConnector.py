"""Local file input connector for ByteIT."""

from pathlib import Path
from typing import Any, Dict, Tuple

from .base import InputConnector


class LocalFileInputConnector(InputConnector):
    """
    Input connector for local files on the machine.

    This connector reads files from the local filesystem and uploads them
    to ByteIT for processing.

    Example:
        >>> connector = LocalFileInputConnector("document.pdf")
        >>> # Or with explicit file type
        >>> connector = LocalFileInputConnector("document.xyz", file_type="pdf")
    """

    def __init__(self, file_path: str):
        """
        Initialize local file input connector.

        Args:
            file_path: Path to the local file to upload

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the path is not a file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")

    def get_file_data(self) -> Tuple[str, Any]:
        """
        Get file data for upload.

        Returns:
            Tuple of (filename, file_object)
        """
        return (self.file_path.name, open(self.file_path, "rb"))

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with connector type and configuration
        """
        return {
            "type": "local_file",
            "path": str(self.file_path),
        }
