"""Tests for exception classes."""

import pytest
from byteit.exceptions import (
    ByteITError,
    AuthenticationError,
    APIKeyError,
    ValidationError,
    ResourceNotFoundError,
    RateLimitError,
    ServerError,
    NetworkError,
    JobProcessingError,
)


class TestByteITError:
    """Test base ByteITError."""

    def test_basic_error(self):
        """Basic error with message."""
        error = ByteITError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.response is None

    def test_error_with_status_code(self):
        """Error with status code."""
        error = ByteITError("Test error", status_code=400)
        assert error.status_code == 400

    def test_error_with_response(self):
        """Error with response data."""
        response_data = {"detail": "Error details"}
        error = ByteITError("Test error", response=response_data)
        assert error.response == response_data

    def test_error_inheritance(self):
        """ByteITError inherits from Exception."""
        error = ByteITError("Test")
        assert isinstance(error, Exception)


class TestAuthenticationErrors:
    """Test authentication-related errors."""

    def test_authentication_error(self):
        """AuthenticationError is ByteITError."""
        error = AuthenticationError("Auth failed")
        assert isinstance(error, ByteITError)
        assert str(error) == "Auth failed"

    def test_api_key_error(self):
        """APIKeyError is AuthenticationError."""
        error = APIKeyError("Invalid key")
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, ByteITError)


class TestValidationError:
    """Test ValidationError."""

    def test_validation_error(self):
        """ValidationError is ByteITError."""
        error = ValidationError("Invalid input")
        assert isinstance(error, ByteITError)
        assert str(error) == "Invalid input"


class TestResourceNotFoundError:
    """Test ResourceNotFoundError."""

    def test_resource_not_found(self):
        """ResourceNotFoundError is ByteITError."""
        error = ResourceNotFoundError("Not found")
        assert isinstance(error, ByteITError)
        assert str(error) == "Not found"


class TestRateLimitError:
    """Test RateLimitError."""

    def test_rate_limit_error(self):
        """RateLimitError is ByteITError."""
        error = RateLimitError("Too many requests")
        assert isinstance(error, ByteITError)


class TestServerError:
    """Test ServerError."""

    def test_server_error(self):
        """ServerError is ByteITError."""
        error = ServerError("Server error", status_code=500)
        assert isinstance(error, ByteITError)
        assert error.status_code == 500


class TestNetworkError:
    """Test NetworkError."""

    def test_network_error(self):
        """NetworkError is ByteITError."""
        error = NetworkError("Connection failed")
        assert isinstance(error, ByteITError)


class TestJobProcessingError:
    """Test JobProcessingError."""

    def test_job_processing_error(self):
        """JobProcessingError is ByteITError."""
        error = JobProcessingError("Processing failed")
        assert isinstance(error, ByteITError)
        assert str(error) == "Processing failed"
