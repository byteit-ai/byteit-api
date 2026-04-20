"""Tests for ByteITClient."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector
from byteit.exceptions import (
    APIKeyError,
    AuthenticationError,
    JobProcessingError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)
from byteit.models.Job import Job
from byteit.models.OutputFormat import OutputFormat


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
            result = client._to_input_connector("test.pdf")  # noqa: F841
            mock_connector.assert_called_once_with(file_path="test.pdf")

    def test_path_object_conversion(self):
        """Path object converts to LocalFileInputConnector."""
        client = ByteITClient("test_key")

        with patch("byteit.ByteITClient.LocalFileInputConnector") as mock_connector:
            mock_connector.return_value = Mock()
            result = client._to_input_connector(Path("test.pdf"))  # noqa: F841
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

        result = client._create_job(connector, output_connector, OutputFormat.TXT)

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

        result = client._create_job(connector, output_connector, OutputFormat.JSON)

        assert isinstance(result, Job)
        assert result.id == "job_123"

    @patch.object(ByteITClient, "_request")
    def test_create_job_serializes_excel_format_as_zip(self, mock_request):
        """Serialize Excel output format as zip in the job creation payload."""
        client = ByteITClient("test_key")
        mock_request.return_value = {
            "job": {
                "id": "job_excel",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "processing_status": "pending",
                "result_format": "zip",
            }
        }

        file_obj = Mock()
        file_obj.closed = False

        connector = Mock()
        connector.to_dict.return_value = {"type": "localfile"}
        connector.get_file_data.return_value = ("test.pdf", file_obj)

        output_connector = Mock()
        output_connector.to_dict.return_value = {"type": "localfile"}

        result = client._create_job(connector, output_connector, OutputFormat.EXCEL)

        assert isinstance(result, Job)
        assert result.result_format == "zip"
        request_kwargs = mock_request.call_args.kwargs
        assert request_kwargs["data"]["output_format"] == "zip"
        file_obj.close.assert_called_once()


class TestWaitForCompletion:
    """Test _wait_for_completion method."""

    @patch("byteit.ByteITClient.ProgressTracker")
    @patch.object(ByteITClient, "_get_job_status")
    @patch("time.sleep")
    def test_wait_returns_on_completion(self, mock_sleep, mock_get_status, mock_tracker):
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
        mock_sleep.assert_called_once_with(1.0)
        mock_tracker.return_value.update.assert_called()
        mock_tracker.return_value.finalize.assert_called_once()

    @patch("byteit.ByteITClient.ProgressTracker")
    @patch.object(ByteITClient, "_get_job_status")
    def test_wait_raises_on_failure(self, mock_get_status, mock_tracker):
        """Failed job raises JobProcessingError."""
        client = ByteITClient("test_key")

        job_failed = Mock()
        job_failed.is_completed = False
        job_failed.is_failed = True
        job_failed.processing_error = "Parse error"

        mock_get_status.return_value = job_failed

        with pytest.raises(JobProcessingError, match="Parse error"):
            client._wait_for_completion("job_123")
        mock_tracker.return_value.close.assert_called_once()

    @patch("byteit.ByteITClient.ProgressTracker")
    @patch.object(ByteITClient, "_get_job_status")
    @patch("time.sleep")
    def test_wait_adaptive_polling_formula(
        self,
        mock_sleep,
        mock_get_status,
        mock_tracker,  # noqa: ARG002
    ):
        """Polling intervals follow MIN(1*1.5^(x-1), 10) formula."""
        client = ByteITClient("test_key")

        job_processing = Mock()
        job_processing.is_completed = False
        job_processing.is_failed = False

        job_complete = Mock()
        job_complete.is_completed = True
        job_complete.is_failed = False

        mock_get_status.side_effect = [
            job_processing,
            job_processing,
            job_processing,
            job_complete,
        ]

        client._wait_for_completion("job_123")

        # Check polling intervals: x=1: 1.0, x=2: 1.5, x=3: 2.25
        assert mock_sleep.call_count == 3
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert calls[0] == 1.0
        assert calls[1] == 1.5
        assert calls[2] == 2.25


class TestParse:
    """Test parse method."""

    @patch.object(ByteITClient, "_download_result")
    @patch.object(ByteITClient, "_wait_for_completion")
    @patch.object(ByteITClient, "_submit_job")
    def test_parse_returns_bytes(
        self,
        mock_submit,
        mock_wait,
        mock_download,
    ):
        """Parse returns result bytes."""
        client = ByteITClient("test_key")

        mock_connector = Mock()
        mock_job = Mock()
        mock_job.id = "job_123"
        mock_submit.return_value = (mock_job, mock_connector)

        mock_download.return_value = b"parsed content"

        result = client.parse("test.pdf")

        assert result == b"parsed content"
        mock_submit.assert_called_once_with("test.pdf", None, OutputFormat.MD, None)
        mock_wait.assert_called_once_with("job_123", input_connector=mock_connector)
        mock_download.assert_called_once_with("job_123")

    @patch.object(ByteITClient, "_try_display_result")
    @patch.object(ByteITClient, "_download_result")
    @patch.object(ByteITClient, "_wait_for_completion")
    @patch.object(ByteITClient, "_submit_job")
    def test_parse_calls_display_when_no_output(
        self,
        mock_submit,
        mock_wait,  # noqa: ARG002
        mock_download,
        mock_display,
    ):
        """Parse calls display when output is None."""
        client = ByteITClient("test_key")

        mock_connector = Mock()
        mock_job = Mock()
        mock_job.id = "job_123"
        mock_submit.return_value = (mock_job, mock_connector)

        mock_download.return_value = b"parsed content"

        result = client.parse("test.pdf", result_format=OutputFormat.JSON)

        assert result == b"parsed content"
        mock_display.assert_called_once_with(b"parsed content", OutputFormat.JSON)

    @patch.object(ByteITClient, "_try_display_result")
    @patch.object(ByteITClient, "_download_result")
    @patch.object(ByteITClient, "_wait_for_completion")
    @patch.object(ByteITClient, "_submit_job")
    def test_parse_converts_string_result_format(
        self,
        mock_submit,
        mock_wait,  # noqa: ARG002
        mock_download,
        mock_display,
    ):
        """Parse converts string result formats before continuing."""
        client = ByteITClient("test_key")

        mock_connector = Mock()
        mock_job = Mock()
        mock_job.id = "job_123"
        mock_submit.return_value = (mock_job, mock_connector)

        mock_download.return_value = b"parsed content"

        result = client.parse("test.pdf", result_format="json")

        assert result == b"parsed content"
        mock_submit.assert_called_once_with("test.pdf", None, OutputFormat.JSON, None)
        mock_display.assert_called_once_with(b"parsed content", OutputFormat.JSON)

    @patch.object(ByteITClient, "_download_result")
    @patch.object(ByteITClient, "_wait_for_completion")
    @patch.object(ByteITClient, "_submit_job")
    @patch("pathlib.Path.write_bytes")
    def test_parse_saves_to_file(
        self,
        mock_write,
        mock_submit,
        mock_wait,
        mock_download,
    ):
        """Parse with output path saves file."""
        client = ByteITClient("test_key")

        mock_connector = Mock()
        mock_job = Mock()
        mock_job.id = "job_123"
        mock_submit.return_value = (mock_job, mock_connector)

        mock_download.return_value = b"parsed content"

        result = client.parse("test.pdf", output="result.txt")

        assert result == b"parsed content"
        mock_write.assert_called_once_with(b"parsed content")
        mock_wait.assert_called_once_with("job_123", input_connector=mock_connector)


class TestParseAsync:
    """Test parse_async method."""

    @patch.object(ByteITClient, "_submit_job")
    def test_parse_async_returns_job(self, mock_submit):
        """parse_async returns Job immediately without waiting."""
        client = ByteITClient("test_key")

        mock_job = Mock(spec=Job)
        mock_job.id = "job_123"
        mock_submit.return_value = (mock_job, Mock())

        result = client.parse_async("test.pdf")

        assert result is mock_job
        mock_submit.assert_called_once_with("test.pdf", None, OutputFormat.MD)

    @patch.object(ByteITClient, "_submit_job")
    def test_parse_async_with_options(self, mock_submit):
        """parse_async forwards processing options."""
        client = ByteITClient("test_key")

        mock_job = Mock(spec=Job)
        mock_job.id = "job_456"
        mock_submit.return_value = (mock_job, Mock())

        opts = {"languages": ["de"], "page_range": "1-3"}
        result = client.parse_async(
            "test.pdf",
            processing_options=opts,
            result_format=OutputFormat.JSON,
        )

        assert result is mock_job
        mock_submit.assert_called_once_with("test.pdf", opts, OutputFormat.JSON)

    @patch.object(ByteITClient, "_submit_job")
    def test_parse_async_converts_string_result_format(self, mock_submit):
        """parse_async converts string result formats before submission."""
        client = ByteITClient("test_key")

        mock_job = Mock(spec=Job)
        mock_job.id = "job_456"
        mock_submit.return_value = (mock_job, Mock())

        result = client.parse_async("test.pdf", result_format="json")

        assert result is mock_job
        mock_submit.assert_called_once_with("test.pdf", None, OutputFormat.JSON)

    @patch.object(ByteITClient, "_submit_job")
    def test_parse_async_converts_excel_name(self, mock_submit):
        """parse_async accepts the public excel string input."""
        client = ByteITClient("test_key")

        mock_job = Mock(spec=Job)
        mock_job.id = "job_excel"
        mock_submit.return_value = (mock_job, Mock())

        result = client.parse_async("test.pdf", result_format="excel")

        assert result is mock_job
        mock_submit.assert_called_once_with("test.pdf", None, OutputFormat.EXCEL)

    def test_parse_async_rejects_zip_string_input(self):
        """parse_async rejects zip as a public string input."""
        client = ByteITClient("test_key")

        with pytest.raises(
            ValidationError,
            match="result_format must be an OutputFormat or one of: "
            + "txt, json, html, md, excel",
        ):
            client.parse_async("test.pdf", result_format="zip")

    @patch.object(ByteITClient, "_submit_job")
    def test_parse_async_does_not_wait(self, mock_submit):
        """parse_async doesn't call _wait_for_completion or _download_result."""
        client = ByteITClient("test_key")

        mock_job = Mock(spec=Job)
        mock_job.id = "job_789"
        mock_submit.return_value = (mock_job, Mock())

        with (
            patch.object(client, "_wait_for_completion") as mock_wait,
            patch.object(client, "_download_result") as mock_download,
        ):
            client.parse_async("test.pdf")
            mock_wait.assert_not_called()
            mock_download.assert_not_called()


class TestSubmitJob:
    """Test _submit_job helper method."""

    @patch.object(ByteITClient, "_create_job")
    @patch.object(ByteITClient, "_to_output_connector")
    @patch.object(ByteITClient, "_to_input_connector")
    def test_submit_job_creates_connectors_and_job(
        self, mock_to_input, mock_to_output, mock_create
    ):
        """_submit_job wires connectors and returns job + input_connector."""
        client = ByteITClient("test_key")

        mock_input_conn = Mock()
        mock_output_conn = Mock()
        mock_job = Mock(spec=Job)
        mock_to_input.return_value = mock_input_conn
        mock_to_output.return_value = mock_output_conn
        mock_create.return_value = mock_job

        job, input_conn = client._submit_job("test.pdf", None, OutputFormat.MD, None)

        assert job is mock_job
        assert input_conn is mock_input_conn
        mock_to_input.assert_called_once_with("test.pdf")
        mock_to_output.assert_called_once_with(None)
        mock_create.assert_called_once_with(
            input_connector=mock_input_conn,
            output_connector=mock_output_conn,
            processing_options=None,
            result_format=OutputFormat.MD,
        )

    @patch.object(ByteITClient, "_create_job")
    @patch.object(ByteITClient, "_to_output_connector")
    @patch.object(ByteITClient, "_to_input_connector")
    def test_submit_job_coerces_dict_to_processing_options(
        self, mock_to_input, mock_to_output, mock_create
    ):
        """_submit_job converts dict to ProcessingOptions."""
        client = ByteITClient("test_key")

        mock_to_input.return_value = Mock()
        mock_to_output.return_value = Mock()
        mock_create.return_value = Mock(spec=Job)

        client._submit_job("test.pdf", {"languages": ["de"]}, OutputFormat.JSON)

        call_kwargs = mock_create.call_args[1]
        from byteit.models.ExtractionType import ExtractionType
        from byteit.models.ProcessingOptions import ProcessingOptions

        assert isinstance(call_kwargs["processing_options"], ProcessingOptions)
        assert call_kwargs["processing_options"].languages == ["de"]

        client._submit_job(
            "test.pdf",
            {"extraction_type": "complex"},
            OutputFormat.JSON,
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["processing_options"].extraction_type is (
            ExtractionType.COMPLEX
        )


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
        # Note: We can't directly check if session is closed without internal access  # noqa: E501


class TestGetJobs:
    """Test job retrieval methods."""

    @patch.object(ByteITClient, "_list_jobs")
    def test_get_jobs(self, mock_list):
        """get_jobs returns job list."""
        client = ByteITClient("test_key")

        mock_job_list = Mock()
        mock_job_list.jobs = [Mock(), Mock()]
        mock_list.return_value = mock_job_list

        result = client.get_jobs()

        assert result == mock_job_list.jobs
        assert len(result) == 2

    @patch.object(ByteITClient, "_get_job_status")
    def test_get_job_status(self, mock_get_status):
        """get_job_status returns specific job."""
        client = ByteITClient("test_key")

        mock_job = Mock()
        mock_get_status.return_value = mock_job

        result = client.get_job_status("job_123")

        assert result == mock_job
        mock_get_status.assert_called_once_with("job_123")

    @patch.object(ByteITClient, "_download_result")
    def test_get_job_result(self, mock_download):
        """get_job_result downloads job result."""
        client = ByteITClient("test_key")

        mock_download.return_value = b"result content"

        result = client.get_job_result("job_123")

        assert result == b"result content"
        mock_download.assert_called_once_with("job_123")


def _make_ipython_mock():
    """Build a minimal sys.modules mock for IPython.display."""
    mock_display_mod = MagicMock()
    mock_ipython = MagicMock()
    mock_ipython.display = mock_display_mod
    return mock_ipython, mock_display_mod


class TestDisplayResult:
    """Test _try_display_result method."""

    def test_display_json_in_notebook(self):
        """Display JSON when IPython is available."""
        client = ByteITClient("test_key")
        mock_ipython, mock_display_mod = _make_ipython_mock()

        with patch.dict(
            sys.modules,
            {"IPython": mock_ipython, "IPython.display": mock_display_mod},
        ):
            client._try_display_result(b'{"key": "value"}', OutputFormat.JSON)

        mock_display_mod.display.assert_called_once()
        mock_display_mod.JSON.assert_called_once()

    def test_display_markdown_in_notebook(self):
        """Display Markdown when IPython is available."""
        client = ByteITClient("test_key")
        mock_ipython, mock_display_mod = _make_ipython_mock()

        with patch.dict(
            sys.modules,
            {"IPython": mock_ipython, "IPython.display": mock_display_mod},
        ):
            client._try_display_result(b"# Header", OutputFormat.MD)

        mock_display_mod.display.assert_called_once()
        mock_display_mod.Markdown.assert_called_once()

    def test_display_html_in_notebook(self):
        """Display HTML when IPython is available."""
        client = ByteITClient("test_key")
        mock_ipython, mock_display_mod = _make_ipython_mock()

        with patch.dict(
            sys.modules,
            {"IPython": mock_ipython, "IPython.display": mock_display_mod},
        ):
            client._try_display_result(b"<h1>Header</h1>", OutputFormat.HTML)

        mock_display_mod.display.assert_called_once()
        mock_display_mod.HTML.assert_called_once()

    def test_display_text_in_notebook(self):
        """Display text with code block when IPython is available."""
        client = ByteITClient("test_key")
        mock_ipython, mock_display_mod = _make_ipython_mock()

        with patch.dict(
            sys.modules,
            {"IPython": mock_ipython, "IPython.display": mock_display_mod},
        ):
            client._try_display_result(b"Plain text", OutputFormat.TXT)

        mock_display_mod.display.assert_called_once()
        mock_display_mod.Markdown.assert_called_once()

    def test_skip_display_for_excel_result(self):
        """Skip notebook display for Excel archive results."""
        client = ByteITClient("test_key")
        mock_ipython, mock_display_mod = _make_ipython_mock()

        with patch.dict(
            sys.modules,
            {"IPython": mock_ipython, "IPython.display": mock_display_mod},
        ):
            client._try_display_result(
                b"PK\x03\x04binary zip content", OutputFormat.EXCEL
            )

        mock_display_mod.display.assert_not_called()

    def test_display_handles_import_error(self):
        """Gracefully skip display when IPython is not available."""
        client = ByteITClient("test_key")
        # Remove IPython from sys.modules to simulate it not being installed
        with patch.dict(sys.modules, {"IPython": None, "IPython.display": None}):
            client._try_display_result(b"test", OutputFormat.TXT)  # must not raise
