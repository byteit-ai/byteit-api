"""ByteIT cloud storage output connector."""  # noqa: N999

from typing import Any

from .base import OutputConnector


class LocalFileOutputConnector(OutputConnector):
    """Output connector that stores results in ByteIT cloud storage.

    Results are stored on ByteIT servers and can be retrieved later
    using the job ID and get_job_result() method.

    This is the default output connector if none is specified.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with connector type
        """
        return {"type": "localfile"}
