"""ByteIT cloud storage output connector."""

from typing import Any, Dict

from .base import OutputConnector


class LocalFileOutputConnector(OutputConnector):
    """
    Output connector that stores results in ByteIT cloud storage.

    Results are stored on ByteIT servers and can be retrieved later
    using the job ID and get_job_result() method.

    This is the default output connector if none is specified.
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with connector type
        """
        return {"type": "localfile"}
