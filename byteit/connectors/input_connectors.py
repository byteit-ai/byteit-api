"""Input connector implementations for ByteIT."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .base import InputConnector


class LocalFileInputConnector(InputConnector):
    """Input connector for local files on the machine."""

    def __init__(self, file_path: str, file_type: Optional[str] = None):
        """
        Initialize local file input connector.

        Args:
            file_path: Path to the local file to upload
            file_type: Optional file type (e.g., 'pdf', 'docx', 'txt').
                      If not provided, will be inferred from file extension.

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the path is not a file or file type cannot be determined
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")

        # Determine file type
        if file_type:
            self.file_type = file_type
        else:
            # Infer from extension
            suffix = self.file_path.suffix.lower().lstrip(".")
            if not suffix:
                raise ValueError(
                    f"Cannot determine file type for {self.file_path}. "
                    "Please provide file_type parameter."
                )
            self.file_type = suffix

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
            "file_type": self.file_type,
        }


# Future connector examples (not yet implemented):
#
# class S3InputConnector(InputConnector):
#     """Input connector for Amazon S3."""
#
#     def __init__(
#         self,
#         bucket: str,
#         key: str,
#         access_key_id: str,
#         secret_access_key: str,
#         region: Optional[str] = None
#     ):
#         """
#         Initialize S3 input connector.
#
#         Args:
#             bucket: S3 bucket name
#             key: S3 object key (file path in bucket)
#             access_key_id: AWS access key ID
#             secret_access_key: AWS secret access key
#             region: AWS region (optional)
#         """
#         self.bucket = bucket
#         self.key = key
#         self.access_key_id = access_key_id
#         self.secret_access_key = secret_access_key
#         self.region = region
#
#     def get_file_data(self) -> Tuple[str, Any]:
#         """Get file data from S3."""
#         # Implementation would download from S3
#         raise NotImplementedError("S3 connector not yet implemented")
#
#     def to_dict(self) -> Dict[str, Any]:
#         """Convert to dictionary representation."""
#         return {
#             "type": "s3",
#             "bucket": self.bucket,
#             "key": self.key,
#             "access_key_id": self.access_key_id,
#             "secret_access_key": self.secret_access_key,
#             "region": self.region,
#         }
#
#
# class GoogleDriveInputConnector(InputConnector):
#     """Input connector for Google Drive."""
#
#     def __init__(self, file_id: str, access_token: str):
#         """
#         Initialize Google Drive input connector.
#
#         Args:
#             file_id: Google Drive file ID
#             access_token: OAuth 2.0 access token
#         """
#         self.file_id = file_id
#         self.access_token = access_token
#
#     def get_file_data(self) -> Tuple[str, Any]:
#         """Get file data from Google Drive."""
#         # Implementation would download from Google Drive
#         raise NotImplementedError("Google Drive connector not yet implemented")
#
#     def to_dict(self) -> Dict[str, Any]:
#         """Convert to dictionary representation."""
#         return {
#             "type": "google_drive",
#             "file_id": self.file_id,
#             "access_token": self.access_token,
#         }
#
#
# class URLInputConnector(InputConnector):
#     """Input connector for downloading files from HTTP/HTTPS URLs."""
#
#     def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
#         """
#         Initialize URL input connector.
#
#         Args:
#             url: HTTP/HTTPS URL to download from
#             headers: Optional HTTP headers for the request
#         """
#         self.url = url
#         self.headers = headers or {}
#
#     def get_file_data(self) -> Tuple[str, Any]:
#         """Download file from URL."""
#         # Implementation would download from URL
#         raise NotImplementedError("URL connector not yet implemented")
#
#     def to_dict(self) -> Dict[str, Any]:
#         """Convert to dictionary representation."""
#         return {
#             "type": "url",
#             "url": self.url,
#             "headers": self.headers,
#         }
