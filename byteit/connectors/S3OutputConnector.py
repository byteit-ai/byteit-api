"""AWS S3 output connector for ByteIT."""

from typing import Any, Dict

from .base import OutputConnector


class S3OutputConnector(OutputConnector):
    """
    Output connector for Amazon S3 using IAM role authentication.

    This connector instructs the ByteIT server to save processed results
    directly to your S3 bucket. The result does NOT pass through your local machine.

    Prerequisites:
        You must first create an AWS connection in ByteIT by providing an IAM
        role ARN that ByteIT can assume to access your S3 bucket.

    Note:
        The ByteIT server will use the IAM role configured in your AWS connection
        to write to the S3 bucket. No AWS credentials are needed in your client code.
    """

    def __init__(
        self,
        bucket: str,
        path: str = "",
    ):
        """
        Initialize S3 output connector.

        Args:
            bucket: S3 bucket name where results will be saved
            path: path prefix within the bucket (e.g., "results/" or "processed/2024/").
        """
        self.bucket = bucket
        self.path = (
            path.rstrip("/") + "/" if path and not path.endswith("/") else path
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize connector configuration for the API.

        Returns:
            Dictionary with connector type and configuration matching API format:
            {"type": "s3", "bucket": "bucket-name", "path": "output/path/"}
        """
        return {
            "type": "s3",
            "bucket": self.bucket,
            "path": self.path,
        }
