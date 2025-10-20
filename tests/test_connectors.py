"""Quick test to verify the connector implementation."""

import sys
from pathlib import Path

# Add the parent directory to the path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from byteit import (
    LocalFileInputConnector,
    ByteITStorageOutputConnector,
    validate_processing_options,
    ValidationError,
)


def test_local_file_input_connector():
    """Test LocalFileInputConnector."""
    print("Testing LocalFileInputConnector...")

    # Create a test file
    test_file = Path("test_doc.txt")
    test_file.write_text("Test content")

    try:
        # Test with auto-detected file type
        connector = LocalFileInputConnector(str(test_file))

        # Test to_dict
        config = connector.to_dict()
        assert config["type"] == "local_file"
        assert "test_doc.txt" in config["path"]
        assert config["file_type"] == "txt"
        print("  ✓ to_dict() works correctly with auto-detected file type")

        # Test get_file_data
        filename, file_obj = connector.get_file_data()
        assert filename == "test_doc.txt"
        assert hasattr(file_obj, "read")
        file_obj.close()
        print("  ✓ get_file_data() works correctly")

        # Test with explicit file type
        connector2 = LocalFileInputConnector(str(test_file), file_type="custom")
        assert connector2.file_type == "custom"
        print("  ✓ Explicit file_type parameter works")

    finally:
        test_file.unlink(missing_ok=True)

    print("✓ LocalFileInputConnector tests passed!\n")


def test_byteit_storage_output_connector():
    """Test ByteITStorageOutputConnector."""
    print("Testing ByteITStorageOutputConnector...")

    connector = ByteITStorageOutputConnector()

    # Test to_dict
    config = connector.to_dict()
    assert config["type"] == "byteit_storage"
    print("  ✓ to_dict() works correctly")

    print("✓ ByteITStorageOutputConnector tests passed!\n")


def test_processing_options_validation():
    """Test processing options validation."""
    print("Testing processing options validation...")

    # Valid options should pass
    valid_options = {
        "ocr_model": "tesseract",
        "vlm_model": "gpt-4-vision",
        "languages": ["en", "de"],
        "page_range": "1-10",
        "output_format": "markdown",
    }

    try:
        validate_processing_options(valid_options)
        print("  ✓ Valid options pass validation")
    except ValidationError:
        print("  ✗ Valid options failed validation")
        raise

    # Invalid options should fail
    invalid_options = {
        "ocr_model": "tesseract",
        "invalid_field": "value",
    }

    try:
        validate_processing_options(invalid_options)
        print("  ✗ Invalid options should have raised ValidationError")
        assert False
    except ValidationError as e:
        print(f"  ✓ Invalid options correctly rejected: {e.message}")

    print("✓ Processing options validation tests passed!\n")


def test_file_not_found():
    """Test that FileNotFoundError is raised for non-existent files."""
    print("Testing file not found handling...")

    try:
        connector = LocalFileInputConnector("non_existent_file.pdf")
        print("  ✗ Should have raised FileNotFoundError")
        assert False
    except FileNotFoundError:
        print("  ✓ FileNotFoundError raised correctly")

    print("✓ File not found handling tests passed!\n")


def test_file_without_extension():
    """Test handling of files without extensions."""
    print("Testing file without extension handling...")

    # Create a test file without extension
    test_file = Path("testfile")
    test_file.write_text("Test content")

    try:
        # Should raise ValueError when file has no extension and no file_type provided
        try:
            connector = LocalFileInputConnector(str(test_file))
            print(
                "  ✗ Should have raised ValueError for file without extension"
            )
            assert False
        except ValueError as e:
            assert "Cannot determine file type" in str(e)
            print("  ✓ ValueError raised correctly for file without extension")

        # Should work when file_type is explicitly provided
        connector = LocalFileInputConnector(str(test_file), file_type="txt")
        assert connector.file_type == "txt"
        print("  ✓ Explicit file_type works for extensionless files")

    finally:
        test_file.unlink(missing_ok=True)

    print("✓ File without extension tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Running ByteIT Connector Tests")
    print("=" * 60)
    print()

    try:
        test_local_file_input_connector()
        test_byteit_storage_output_connector()
        test_processing_options_validation()
        test_file_not_found()
        test_file_without_extension()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
