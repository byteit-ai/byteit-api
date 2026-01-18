"""Integration tests for ByteIT SDK.

These tests require a running ByteIT API server and valid API key.
They are skipped by default - use pytest -m integration to run them.
"""

import os
import pytest
from pathlib import Path
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector


# Skip integration tests by default
pytestmark = pytest.mark.integration


@pytest.fixture
def api_key():
    """Get API key from environment."""
    key = os.getenv("BYTEIT_API_KEY")
    if not key:
        pytest.skip("BYTEIT_API_KEY not set")
    return key


@pytest.fixture
def client(api_key):
    """Create ByteIT client."""
    return ByteITClient(api_key)


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample PDF for testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Sample document for testing ByteIT SDK")
    return file_path


class TestIntegrationParse:
    """Integration tests for parse method."""

    def test_parse_local_file(self, client, sample_file):
        """Parse a local file end-to-end."""
        result = client.parse(str(sample_file), output_format="txt")

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_parse_with_output_file(self, client, sample_file, tmp_path):
        """Parse and save to output file."""
        output_file = tmp_path / "output.txt"

        result = client.parse(
            str(sample_file), output_format="txt", output=str(output_file)
        )

        assert isinstance(result, bytes)
        assert output_file.exists()
        assert output_file.read_bytes() == result

    def test_parse_different_formats(self, client, sample_file):
        """Parse with different output formats."""
        formats = ["txt", "json", "md", "html"]

        for fmt in formats:
            result = client.parse(str(sample_file), output_format=fmt)
            assert isinstance(result, bytes)
            assert len(result) > 0


class TestIntegrationJobs:
    """Integration tests for job management."""

    def test_get_all_jobs(self, client):
        """List all jobs."""
        jobs = client.get_all_jobs()
        assert isinstance(jobs, list)

    def test_get_job_by_id(self, client, sample_file):
        """Get specific job by ID."""
        # Create a job first
        result = client.parse(str(sample_file))

        # Get all jobs and find the one we just created
        jobs = client.get_all_jobs()
        if jobs:
            job = client.get_job_by_id(jobs[0].id)
            assert job.id == jobs[0].id


class TestIntegrationContextManager:
    """Integration test for context manager."""

    def test_context_manager(self, api_key, sample_file):
        """Client works as context manager."""
        with ByteITClient(api_key) as client:
            result = client.parse(str(sample_file))
            assert isinstance(result, bytes)
