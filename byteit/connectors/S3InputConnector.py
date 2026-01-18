"""AWS S3 input connector for ByteIT."""

from pathlib import Path
from typing import Any, Dict, Tuple

from .base import InputConnector


class S3InputConnector(InputConnector):
    """AWS S3 input connector with IAM role authentication.

    Instructs ByteIT servers to fetch files directly from your S3 bucket
    using IAM role assumption. Files never pass through your local machine,
    providing faster processing and reduced bandwidth usage.

    Prerequisites:
        - Create an AWS connection in ByteIT dashboard
        - Provide an IAM role ARN that ByteIT can assume
        - Grant the role read access to your S3 bucket

    Args:
        source_bucket: S3 bucket name
        source_path_inside_bucket: Object key/path within bucket

    Note:
        No AWS credentials needed in client code - ByteIT uses the
        IAM role configured in your account settings.

    Example:
        connector = S3InputConnector(
            source_bucket="my-documents",
            source_path_inside_bucket="invoices/2024/jan.pdf"
        )
        result = client.parse(connector)
    """

    def __init__(
        self,
        source_bucket: str,
        source_path_inside_bucket: str,
    ):
        """
        Initialize S3 input connector.

        Args:
            source_bucket: S3 bucket name where the file is located
            source_path_inside_bucket: Path to the file within the bucket (e.g., "folder/file.pdf")
        """
        self.source_bucket = source_bucket
        self.source_path_inside_bucket = source_path_inside_bucket

        # Extract filename for display
        self.filename = Path(source_path_inside_bucket).name

    def get_file_data(self) -> Tuple[str, Dict[str, Any]]:
        """
        Return connection configuration for the ByteIT server.

        This method does NOT download the file. Instead, it returns metadata
        that tells the ByteIT server how to fetch the file from S3.

        Returns:
            Tuple of (filename, connection_data_dict)
        """
        connection_data = {
            "source_bucket": self.source_bucket,
            "source_path_inside_bucket": self.source_path_inside_bucket,
        }
        return (self.filename, connection_data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize connector configuration.

        Returns:
            Dictionary with connector type and configuration
        """
        return {
            "type": "s3",
            "source_bucket": self.source_bucket,
            "source_path_inside_bucket": self.source_path_inside_bucket,
        }
