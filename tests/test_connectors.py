"""Tests for connector classes."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from byteit.connectors import (
    LocalFileInputConnector,
    S3InputConnector,
    LocalFileOutputConnector,
)


class TestLocalFileInputConnector:
    """Test LocalFileInputConnector."""

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_init_with_valid_file(self, mock_is_file, mock_exists):
        """Valid file path initializes correctly."""
        mock_exists.return_value = True
        mock_is_file.return_value = True

        connector = LocalFileInputConnector("test.pdf")

        assert connector.file_path == Path("test.pdf")

    @patch("pathlib.Path.exists")
    def test_init_with_nonexistent_file(self, mock_exists):
        """Nonexistent file raises FileNotFoundError."""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match="File not found"):
            LocalFileInputConnector("missing.pdf")

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_init_with_directory(self, mock_is_file, mock_exists):
        """Directory path raises ValueError."""
        mock_exists.return_value = True
        mock_is_file.return_value = False

        with pytest.raises(ValueError, match="Path is not a file"):
            LocalFileInputConnector("some_directory")

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @patch("builtins.open", new_callable=mock_open, read_data=b"file content")
    def test_get_file_data(self, mock_file, mock_is_file, mock_exists):
        """get_file_data returns filename and file object."""
        mock_exists.return_value = True
        mock_is_file.return_value = True

        connector = LocalFileInputConnector("test.pdf")
        filename, file_obj = connector.get_file_data()

        assert filename == "test.pdf"
        assert file_obj is not None

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_to_dict(self, mock_is_file, mock_exists):
        """to_dict returns correct configuration."""
        mock_exists.return_value = True
        mock_is_file.return_value = True

        connector = LocalFileInputConnector("test.pdf")
        result = connector.to_dict()

        assert result["type"] == "localfile"
        assert "test.pdf" in result["path"]


class TestS3InputConnector:
    """Test S3InputConnector."""

    def test_init(self):
        """S3 connector initializes with bucket and path."""
        connector = S3InputConnector(
            source_bucket="my-bucket", source_path_inside_bucket="docs/file.pdf"
        )

        assert connector.source_bucket == "my-bucket"
        assert connector.source_path_inside_bucket == "docs/file.pdf"
        assert connector.filename == "file.pdf"

    def test_get_file_data(self):
        """get_file_data returns connection configuration."""
        connector = S3InputConnector(
            source_bucket="my-bucket", source_path_inside_bucket="docs/file.pdf"
        )

        filename, connection_data = connector.get_file_data()

        assert filename == "file.pdf"
        assert connection_data["source_bucket"] == "my-bucket"
        assert connection_data["source_path_inside_bucket"] == "docs/file.pdf"

    def test_to_dict(self):
        """to_dict returns correct configuration."""
        connector = S3InputConnector(
            source_bucket="my-bucket", source_path_inside_bucket="docs/file.pdf"
        )

        result = connector.to_dict()

        assert result["type"] == "s3"
        assert result["source_bucket"] == "my-bucket"
        assert result["source_path_inside_bucket"] == "docs/file.pdf"

    def test_nested_path(self):
        """Handles nested paths correctly."""
        connector = S3InputConnector(
            source_bucket="bucket", source_path_inside_bucket="a/b/c/file.pdf"
        )

        assert connector.filename == "file.pdf"


class TestLocalOutputConnector:
    """Test LocalOutputConnector."""

    def test_to_dict(self):
        """to_dict returns local connector config."""
        connector = LocalFileOutputConnector()
        result = connector.to_dict()

        assert result["type"] == "localfile"
