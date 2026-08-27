"""Tests for package-level initialization helpers."""

from unittest.mock import Mock, patch

import byteit


class TestPackageVersionCheck:
    """Test import-time version mismatch warning helpers."""

    @patch.object(byteit, "_should_check_latest_version", return_value=True)
    @patch.object(byteit.warnings, "warn")
    @patch.object(byteit.requests, "get")
    def test_warns_when_pypi_version_differs(
        self,
        mock_get,
        mock_warn,
        mock_should_check,
    ):
        """A warning is emitted when runtime and PyPI versions differ."""
        response = Mock()
        response.json.return_value = {"info": {"version": "9.9.9"}}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        byteit._check_latest_version()

        mock_should_check.assert_called_once_with()
        mock_get.assert_called_once_with("https://pypi.org/pypi/byteit/json", timeout=2)
        mock_warn.assert_called_once()
        warning_message = mock_warn.call_args.args[0]
        assert f"local version is {byteit.__version__}" in warning_message
        assert "published PyPI version is 9.9.9" in warning_message

    @patch.object(byteit, "_should_check_latest_version", return_value=True)
    @patch.object(byteit.warnings, "warn")
    @patch.object(byteit.requests, "get")
    def test_skips_warning_when_pypi_version_matches(
        self,
        mock_get,
        mock_warn,
        mock_should_check,
    ):
        """No warning is emitted when versions already match."""
        response = Mock()
        response.json.return_value = {"info": {"version": byteit.__version__}}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        byteit._check_latest_version()

        mock_should_check.assert_called_once_with()
        mock_warn.assert_not_called()

    @patch.object(byteit, "_should_check_latest_version", return_value=True)
    @patch.object(byteit.warnings, "warn")
    @patch.object(byteit.requests, "get", side_effect=RuntimeError("network down"))
    def test_swallows_network_failures(
        self,
        mock_get,
        mock_warn,
        mock_should_check,
    ):
        """Version checks never break imports when PyPI lookup fails."""
        byteit._check_latest_version()

        mock_should_check.assert_called_once_with()
        mock_get.assert_called_once_with("https://pypi.org/pypi/byteit/json", timeout=2)
        mock_warn.assert_not_called()


def test_saved_schema_models_are_exported() -> None:
    """Saved schema models are available from the package root."""
    assert byteit.SavedSchema.__name__ == "SavedSchema"
    assert byteit.SavedSchemaList.__name__ == "SavedSchemaList"
