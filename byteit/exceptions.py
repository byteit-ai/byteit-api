"""Custom exceptions for the ByteIT client library."""

from typing import Any


class ByteITError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
        self.status_code = status_code
        self.response = response


class AuthenticationError(ByteITError):
    """Raised when authentication fails."""

    pass


class APIKeyError(AuthenticationError):
    """Raised when there's an issue with the API key."""

    pass


class ValidationError(ByteITError):
    """Raised when request validation fails."""

    pass


class ResourceNotFoundError(ByteITError):
    """Raised when a requested resource is not found."""

    pass


class RateLimitError(ByteITError):
    """Raised when rate limit is exceeded."""

    pass


class ServerError(ByteITError):
    """Raised when the server encounters an error."""

    pass


class NetworkError(ByteITError):
    """Raised when a network error occurs."""

    pass


class JobProcessingError(ByteITError):
    """Raised when job processing fails."""

    pass
