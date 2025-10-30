"""AWS S3 input connector for ByteIT."""

from pathlib import Path
from typing import Any, Dict, Tuple

from .base import InputConnector


class S3InputConnector(InputConnector):
    """
    Input connector for Amazon S3 using IAM role authentication.

    This connector instructs the ByteIT server to fetch files directly from
    your S3 bucket using IAM role assumption. The file does NOT pass through
    your local machine.

    Prerequisites:
        You must first create an AWS connection in ByteIT by providing an IAM
        role ARN that ByteIT can assume to access your S3 bucket.

    Example:
        >>> # First, set up AWS connection (one-time setup via ByteIT dashboard or API)
        >>> # Then use the connector:
        >>> connector = S3InputConnector(
        ...     source_bucket="my-documents",
        ...     source_path_inside_bucket="invoices/invoice-001.pdf"
        ... )
        >>> job = client.create_job(input_connector=connector)

    Note:
        The ByteIT server will use the IAM role configured in your AWS connection
        to access the S3 bucket. No AWS credentials are needed in your client code.
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
