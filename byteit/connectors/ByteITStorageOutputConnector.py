"""ByteIT cloud storage output connector."""

from typing import Any, Dict

from .base import OutputConnector


class ByteITStorageOutputConnector(OutputConnector):
    """
    Output connector that stores results in ByteIT cloud storage.

    Results are stored on ByteIT servers and can be retrieved later
    using the job ID and get_job_result() method.

    This is the default output connector if none is specified.

    Example:
        >>> connector = ByteITStorageOutputConnector()
        >>> result = client.process_document(
        ...     input_connector=input_conn,
        ...     output_connector=connector
        ... )
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
