"""Local file input connector for ByteIT."""

from pathlib import Path
from typing import Any, Dict, Tuple

from .base import InputConnector


class LocalFileInputConnector(InputConnector):
    """Local file input connector.

    Reads files from your local filesystem and uploads them to ByteIT.
    The file is read and transmitted from your machine to ByteIT servers.

    Args:
        file_path: Path to the local file

    Raises:
        FileNotFoundError: File doesn't exist at specified path
        ValueError: Path is a directory, not a file

    Example:
        connector = LocalFileInputConnector("/path/to/document.pdf")
        result = client.parse(connector)
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
            "type": "localfile",
            "path": str(self.file_path),
        }
