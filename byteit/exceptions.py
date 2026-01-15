"""Custom exceptions for the ByteIT client library."""

from typing import Any


class ByteITError(Exception):
    """Base exception for all ByteIT API errors.

    All ByteIT exceptions inherit from this class, making it easy to catch
    any ByteIT-related error with a single except clause.

    Attributes:
        message: Human-readable error description
        status_code: HTTP status code if available
        response: Full API response data if available
    """

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


class AuthenticationError(ByteITError):
    """Authentication failure.

    Raised when API requests fail due to invalid or missing credentials.
    Check your API key and ensure it's properly configured.
    """

    pass


class APIKeyError(AuthenticationError):
    """API key validation error.

    Raised when the provided API key is invalid, expired, or missing.
    Verify your API key at https://byteit.ai/dashboard.
    """

    pass


class ValidationError(ByteITError):
    """Request validation error.

    Raised when request parameters are invalid or missing required fields.
    Check the error message for details on which parameters need correction.
    """

    pass


class ResourceNotFoundError(ByteITError):
    """Resource not found.

    Raised when attempting to access a job or resource that doesn't exist
    or that you don't have permission to access.
    """

    pass


class RateLimitError(ByteITError):
    """Rate limit exceeded.

    Raised when you've exceeded your API rate limits.
    Wait before retrying or contact support to increase your limits.
    """

    pass


class ServerError(ByteITError):
    """Server-side error.

    Raised when ByteIT servers encounter an internal error (5xx status codes).
    These errors are usually temporary - retry after a brief delay.
    """

    pass


class NetworkError(ByteITError):
    """Network communication error.

    Raised when unable to reach ByteIT servers due to network issues.
    Check your internet connection and firewall settings.
    """

    pass


class JobProcessingError(ByteITError):
    """Job processing failure.

    Raised when a document processing job fails or cannot be completed.
    Check the error message for specific details about the failure.
    """

    pass
