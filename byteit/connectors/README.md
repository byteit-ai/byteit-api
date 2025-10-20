# ByteIT Connectors

This directory contains all connector implementations for the ByteIT library.

## Structure

```
connectors/
├── __init__.py              # Package initialization and exports
├── base.py                  # Base abstract classes
├── input_connectors.py      # Input connector implementations
└── output_connectors.py     # Output connector implementations
```

## Base Classes

### `InputConnector` (Abstract)
Base class for all input connectors that provide file data to ByteIT.

**Required methods:**
- `get_file_data() -> Tuple[str, Any]`: Returns (filename, file_object)
- `to_dict() -> Dict[str, Any]`: Serializes connector configuration

### `OutputConnector` (Abstract)
Base class for all output connectors that handle processed results.

**Required methods:**
- `to_dict() -> Dict[str, Any]`: Serializes connector configuration

## Implemented Connectors

### Input Connectors

#### `LocalFileInputConnector`
Upload files from the local filesystem.

```python
from byteit import LocalFileInputConnector

connector = LocalFileInputConnector("path/to/file.pdf")
```

### Output Connectors

#### `ByteITStorageOutputConnector`
Store results on ByteIT cloud storage (default).

```python
from byteit import ByteITStorageOutputConnector

connector = ByteITStorageOutputConnector()
```

## Adding New Connectors

### Input Connector Example

1. Add your connector class to `input_connectors.py`:

```python
class MyInputConnector(InputConnector):
    def __init__(self, custom_params):
        self.custom_params = custom_params
    
    def get_file_data(self) -> Tuple[str, Any]:
        # Implement file retrieval logic
        filename = "file.pdf"
        file_object = self._fetch_file()
        return (filename, file_object)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "my_connector",
            "params": self.custom_params
        }
```

2. Export it in `__init__.py`:

```python
from .input_connectors import LocalFileInputConnector, MyInputConnector

__all__ = [
    # ... other exports
    "MyInputConnector",
]
```

### Output Connector Example

1. Add your connector class to `output_connectors.py`:

```python
class MyOutputConnector(OutputConnector):
    def __init__(self, destination):
        self.destination = destination
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "my_output",
            "destination": self.destination
        }
```

2. Export it in `__init__.py`:

```python
from .output_connectors import ByteITStorageOutputConnector, MyOutputConnector

__all__ = [
    # ... other exports
    "MyOutputConnector",
]
```

## Planned Future Connectors

See comments in `input_connectors.py` and `output_connectors.py` for examples of:

### Input Connectors
- **S3InputConnector**: Amazon S3 buckets
- **GoogleDriveInputConnector**: Google Drive files
- **URLInputConnector**: Download from HTTP/HTTPS URLs
- **AzureBlobInputConnector**: Azure Blob Storage

### Output Connectors
- **S3OutputConnector**: Save to Amazon S3
- **GoogleDriveOutputConnector**: Save to Google Drive
- **WebhookOutputConnector**: POST results to webhooks
- **AzureBlobOutputConnector**: Save to Azure Blob Storage

## Testing

Test your connector implementations by adding tests to `tests/test_connectors.py`.

Example:
```python
def test_my_connector():
    connector = MyInputConnector("test_param")
    
    # Test to_dict
    config = connector.to_dict()
    assert config["type"] == "my_connector"
    
    # Test get_file_data
    filename, file_obj = connector.get_file_data()
    assert filename is not None
```
