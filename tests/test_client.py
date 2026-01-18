"""Tests for ByteITClient."""

import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import pytest
import requests

from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector, S3InputConnector
from byteit.exceptions import (
    APIKeyError,
    AuthenticationError,
    ValidationError,
    ResourceNotFoundError,
    JobProcessingError,
    ServerError,
)
from byteit.models.Job import Job


class TestByteITClientInit:
    """Test client initialization."""

    def test_init_with_valid_key(self):
        """Client initializes with valid API key."""
        client = ByteITClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert "X-API-Key" in client._session.headers
        assert client._session.headers["X-API-Key"] == "test_key"

    def test_init_with_empty_key(self):
        """Empty API key raises APIKeyError."""
        with pytest.raises(APIKeyError, match="API key must be a non-empty string"):
            ByteITClient(api_key="")

    def test_init_without_key(self):
        """Missing API key raises APIKeyError."""
        with pytest.raises(APIKeyError, match="API key must be a non-empty string"):
            ByteITClient(api_key=None)


class TestInputConnectorConversion:
    """Test _to_input_connector method."""

    def test_str_path_conversion(self):
        """String path converts to LocalFileInputConnector."""
        client = ByteITClient("test_key")

        with patch("byteit.ByteITClient.LocalFileInputConnector") as mock_connector:
            mock_connector.return_value = Mock()
            result = client._to_input_connector("test.pdf")
            mock_connector.assert_called_once_with(file_path="test.pdf")

    def test_path_object_conversion(self):
        """Path object converts to LocalFileInputConnector."""
        client = ByteITClient("test_key")

        with patch("byteit.ByteITClient.LocalFileInputConnector") as mock_connector:
            mock_connector.return_value = Mock()
            result = client._to_input_connector(Path("test.pdf"))
            mock_connector.assert_called_once_with(file_path="test.pdf")

    def test_connector_passthrough(self):
        """InputConnector passes through unchanged."""
        client = ByteITClient("test_key")
        # Create a mock connector that behaves like InputConnector
        connector = Mock(spec=LocalFileInputConnector)
        connector.to_dict = Mock(return_value={"type": "localfile"})

        result = client._to_input_connector(connector)
        assert result is connector

    def test_invalid_type_raises_error(self):
        """Invalid input type raises ValidationError."""
        client = ByteITClient("test_key")

        with pytest.raises(ValidationError, match="Unsupported input type"):
            client._to_input_connector(123)


class TestHandleResponse:
    """Test _handle_response method."""

    def test_success_with_json(self):
        """200 response with JSON returns data."""
        client = ByteITClient("test_key")
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.content = b'{"key": "value"}'
        response.json.return_value = {"key": "value"}

        result = client._handle_response(response)
        assert result == {"key": "value"}

    def test_success_without_content(self):
        """200 response without content returns empty dict."""
        client = ByteITClient("test_key")
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.content = b""

        result = client._handle_response(response)
        assert result == {}

    def test_400_raises_validation_error(self):
        """400 status raises ValidationError."""
        client = ByteITClient("test_key")
        response = Mock(spec=requests.Response)
        response.status_code = 400
        response.content = b'{"detail": "Invalid format"}'
        response.json.return_value = {"detail": "Invalid format"}
        response.text = "Invalid format"

        with pytest.raises(ValidationError, match="Invalid format"):
            client._handle_response(response)

    def test_401_raises_authentication_error(self):
        """401 status raises AuthenticationError."""
        client = ByteITClient("test_key")
        response = Mock(spec=requests.Response)
        response.status_code = 401
        response.content = b'{"detail": "Unauthorized"}'
        response.json.return_value = {"detail": "Unauthorized"}
        response.text = "Unauthorized"

        with pytest.raises(AuthenticationError, match="Unauthorized"):
            client._handle_response(response)

    def test_403_raises_api_key_error(self):
        """403 status raises APIKeyError."""
        client = ByteITClient("test_key")
        response = Mock(spec=requests.Response)
        response.status_code = 403
        response.content = b'{"detail": "Forbidden"}'
        response.json.return_value = {"detail": "Forbidden"}
        response.text = "Forbidden"

        with pytest.raises(APIKeyError, match="Forbidden"):
            client._handle_response(response)

    def test_404_raises_resource_not_found(self):
        """404 status raises ResourceNotFoundError."""
        client = ByteITClient("test_key")
        response = Mock(spec=requests.Response)
        response.status_code = 404
        response.content = b'{"detail": "Not found"}'
        response.json.return_value = {"detail": "Not found"}
        response.text = "Not found"

        with pytest.raises(ResourceNotFoundError, match="Not found"):
            client._handle_response(response)

    def test_500_raises_server_error(self):
        """500 status raises ServerError."""
        client = ByteITClient("test_key")
        response = Mock(spec=requests.Response)
        response.status_code = 500
        response.content = b'{"detail": "Internal error"}'
        response.json.return_value = {"detail": "Internal error"}
        response.text = "Internal error"

        with pytest.raises(ServerError, match="Internal error"):
            client._handle_response(response)

    def test_error_without_detail(self):
        """Error response without detail uses fallback message."""
        client = ByteITClient("test_key")
        response = Mock(spec=requests.Response)
        response.status_code = 400
        response.content = b"{}"
        response.json.return_value = {}
        response.text = "Bad Request"

        with pytest.raises(ValidationError, match="Bad Request"):
            client._handle_response(response)


class TestCreateJob:
    """Test _create_job method."""

    @patch.object(ByteITClient, "_request")
    @patch.object(ByteITClient, "_get_job_status")
    def test_create_job_with_local_file(self, mock_get_status, mock_request):
        """Create job with local file uploads correctly."""
        client = ByteITClient("test_key")
        mock_request.return_value = {"job_id": "job_123"}
        mock_job = Mock(spec=Job)
        mock_get_status.return_value = mock_job

        connector = Mock()
        connector.to_dict.return_value = {"type": "localfile"}
        connector.get_file_data.return_value = ("test.pdf", Mock())

        output_connector = Mock()
        output_connector.to_dict.return_value = {"type": "localfile"}

        result = client._create_job(connector, output_connector, "txt")

        assert result == mock_job
        mock_request.assert_called_once()
        mock_get_status.assert_called_once_with("job_123")

    @patch.object(ByteITClient, "_request")
    def test_create_job_with_s3(self, mock_request):
        """Create job with S3 connector."""
        client = ByteITClient("test_key")
        mock_job_data = {
            "job": {
                "id": "job_123",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "processing_status": "pending",
                "result_format": "txt",
            }
        }
        mock_request.return_value = mock_job_data

        connector = Mock()
        connector.to_dict.return_value = {"type": "s3"}
        connector.get_file_data.return_value = (
            "test.pdf",
            {"bucket": "test", "key": "test.pdf"},
        )

        output_connector = Mock()
        output_connector.to_dict.return_value = {"type": "localfile"}

        result = client._create_job(connector, output_connector, "json")

        assert isinstance(result, Job)
        assert result.id == "job_123"


class TestWaitForCompletion:
    """Test _wait_for_completion method."""

    @patch.object(ByteITClient, "_get_job_status")
    @patch("time.sleep")
    def test_wait_returns_on_completion(self, mock_sleep, mock_get_status):
        """Polling stops when job completes."""
        client = ByteITClient("test_key")

        job_pending = Mock()
        job_pending.is_completed = False
        job_pending.is_failed = False

        job_complete = Mock()
        job_complete.is_completed = True
        job_complete.is_failed = False

        mock_get_status.side_effect = [job_pending, job_complete]

        result = client._wait_for_completion("job_123")

        assert result == job_complete
        assert mock_get_status.call_count == 2
        mock_sleep.assert_called_once_with(2)

    @patch.object(ByteITClient, "_get_job_status")
    def test_wait_raises_on_failure(self, mock_get_status):
        """Failed job raises JobProcessingError."""
        client = ByteITClient("test_key")

        job_failed = Mock()
        job_failed.is_completed = False
        job_failed.is_failed = True
        job_failed.processing_error = "Parse error"

        mock_get_status.return_value = job_failed

        with pytest.raises(JobProcessingError, match="Parse error"):
            client._wait_for_completion("job_123")


class TestParse:
    """Test parse method."""

    @patch.object(ByteITClient, "_download_result")
    @patch.object(ByteITClient, "_wait_for_completion")
    @patch.object(ByteITClient, "_create_job")
    @patch.object(ByteITClient, "_to_input_connector")
    @patch.object(ByteITClient, "_to_output_connector")
    def test_parse_returns_bytes(
        self, mock_to_output, mock_to_input, mock_create, mock_wait, mock_download
    ):
        """Parse returns result bytes."""
        client = ByteITClient("test_key")

        mock_connector = Mock()
        mock_to_input.return_value = mock_connector
        mock_to_output.return_value = Mock()

        mock_job = Mock()
        mock_job.id = "job_123"
        mock_create.return_value = mock_job

        mock_download.return_value = b"parsed content"

        result = client.parse("test.pdf")

        assert result == b"parsed content"
        mock_to_input.assert_called_once_with("test.pdf")
        mock_create.assert_called_once()
        mock_wait.assert_called_once_with("job_123")
        mock_download.assert_called_once_with("job_123")

    @patch.object(ByteITClient, "_download_result")
    @patch.object(ByteITClient, "_wait_for_completion")
    @patch.object(ByteITClient, "_create_job")
    @patch.object(ByteITClient, "_to_input_connector")
    @patch.object(ByteITClient, "_to_output_connector")
    @patch("pathlib.Path.write_bytes")
    def test_parse_saves_to_file(
        self,
        mock_write,
        mock_to_output,
        mock_to_input,
        mock_create,
        mock_wait,
        mock_download,
    ):
        """Parse with output path saves file."""
        client = ByteITClient("test_key")

        mock_to_input.return_value = Mock()
        mock_to_output.return_value = Mock()

        mock_job = Mock()
        mock_job.id = "job_123"
        mock_create.return_value = mock_job

        mock_download.return_value = b"parsed content"

        result = client.parse("test.pdf", output="result.txt")

        assert result == b"parsed content"
        mock_write.assert_called_once_with(b"parsed content")


class TestContextManager:
    """Test context manager functionality."""

    def test_context_manager(self):
        """Client works as context manager."""
        with ByteITClient("test_key") as client:
            assert isinstance(client, ByteITClient)
            # Session should be active during context
            assert client._session is not None

    def test_session_closes(self):
        """Session closes on exit."""
        client = ByteITClient("test_key")
        with client:
            pass
        # Session should be closed after context exit
        # Note: We can't directly check if session is closed without internal access


class TestGetJobs:
    """Test job retrieval methods."""

    @patch.object(ByteITClient, "_list_jobs")
    def test_get_all_jobs(self, mock_list):
        """get_all_jobs returns job list."""
        client = ByteITClient("test_key")

        mock_job_list = Mock()
        mock_job_list.jobs = [Mock(), Mock()]
        mock_list.return_value = mock_job_list

        result = client.get_all_jobs()

        assert result == mock_job_list.jobs
        assert len(result) == 2

    @patch.object(ByteITClient, "_get_job_status")
    def test_get_job_by_id(self, mock_get_status):
        """get_job_by_id returns specific job."""
        client = ByteITClient("test_key")

        mock_job = Mock()
        mock_get_status.return_value = mock_job

        result = client.get_job_by_id("job_123")

        assert result == mock_job
        mock_get_status.assert_called_once_with("job_123")

    @patch.object(ByteITClient, "_download_result")
    def test_get_result(self, mock_download):
        """get_result downloads job result."""
        client = ByteITClient("test_key")

        mock_download.return_value = b"result content"

        result = client.get_result("job_123")

        assert result == b"result content"
        mock_download.assert_called_once_with("job_123")
