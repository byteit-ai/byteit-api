"""Output connector implementations for ByteIT."""

from typing import Any, Dict

from .base import OutputConnector


class ByteITStorageOutputConnector(OutputConnector):
    """
    Output connector that stores results in ByteIT cloud storage.

    Results are stored on ByteIT servers and can be retrieved later
    using the job ID and get_job_result() method.
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with connector type
        """
        return {
            "type": "byteit_storage",
        }


# Future connector examples (not yet implemented):
#
# class S3OutputConnector(OutputConnector):
#     """Output connector for Amazon S3."""
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
#         Initialize S3 output connector.
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
#     def to_dict(self) -> Dict[str, Any]:
#         """Convert to dictionary representation."""
#         return {
#             "type": "s3_output",
#             "bucket": self.bucket,
#             "key": self.key,
#             "access_key_id": self.access_key_id,
#             "secret_access_key": self.secret_access_key,
#             "region": self.region,
#         }
#
#
# class GoogleDriveOutputConnector(OutputConnector):
#     """Output connector for Google Drive."""
#
#     def __init__(self, folder_id: str, access_token: str, filename: Optional[str] = None):
#         """
#         Initialize Google Drive output connector.
#
#         Args:
#             folder_id: Google Drive folder ID where results will be saved
#             access_token: OAuth 2.0 access token
#             filename: Optional filename for the result (if not provided, server decides)
#         """
#         self.folder_id = folder_id
#         self.access_token = access_token
#         self.filename = filename
#
#     def to_dict(self) -> Dict[str, Any]:
#         """Convert to dictionary representation."""
#         config = {
#             "type": "google_drive_output",
#             "folder_id": self.folder_id,
#             "access_token": self.access_token,
#         }
#         if self.filename:
#             config["filename"] = self.filename
#         return config
#
#
# class WebhookOutputConnector(OutputConnector):
#     """Output connector that POSTs results to a webhook URL."""
#
#     def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
#         """
#         Initialize webhook output connector.
#
#         Args:
#             url: Webhook URL to POST results to
#             headers: Optional HTTP headers for the POST request
#         """
#         self.url = url
#         self.headers = headers or {}
#
#     def to_dict(self) -> Dict[str, Any]:
#         """Convert to dictionary representation."""
#         return {
#             "type": "webhook",
#             "url": self.url,
#             "headers": self.headers,
#         }
