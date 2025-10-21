# ByteIT Connectors

This directory contains all connector implementations for the ByteIT library.

## Structure

```
connectors/
├── __init__.py                          # Package initialization and exports
├── base.py                              # Base abstract classes
├── LocalFileInputConnector.py           # Local file input connector
├── ByteITStorageOutputConnector.py      # ByteIT cloud storage output connector
├── S3InputConnector.py                  # AWS S3 input connector
├── S3OutputConnector.py                 # AWS S3 output connector
└── README.md                            # This file
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
from byteit.connectors import LocalFileInputConnector

# Automatic file type detection
connector = LocalFileInputConnector("path/to/file.pdf")

# Explicit file type
connector = LocalFileInputConnector("path/to/file.xyz", file_type="pdf")
```

**Parameters:**
- `file_path` (str): Path to the local file
- `file_type` (Optional[str]): File type override (auto-detected from extension if not provided)

**Raises:**
- `FileNotFoundError`: If the file doesn't exist
- `ValueError`: If the path is not a file or file type cannot be determined

---

#### `S3InputConnector`
Download and process files from AWS S3 buckets.

```python
from byteit.connectors import S3InputConnector

connector = S3InputConnector(
    bucket="my-bucket",
    key="documents/file.pdf",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"  # Optional
)
```

**Parameters:**
- `bucket` (str): S3 bucket name
- `key` (str): S3 object key (file path in bucket)
- `aws_access_key_id` (Optional[str]): AWS access key (uses boto3 defaults if not provided)
- `aws_secret_access_key` (Optional[str]): AWS secret key (uses boto3 defaults if not provided)
- `region` (Optional[str]): AWS region (uses boto3 defaults if not provided)
- `file_type` (Optional[str]): File type override (auto-detected from key extension if not provided)

**Requirements:**
- Install boto3: `pip install boto3`

**Raises:**
- `ImportError`: If boto3 is not installed
- `ValueError`: If file type cannot be determined
- `botocore.exceptions.ClientError`: If S3 download fails

### Output Connectors

#### `ByteITStorageOutputConnector`
Store results on ByteIT cloud storage (default).

```python
from byteit.connectors import ByteITStorageOutputConnector

connector = ByteITStorageOutputConnector()
```

Results are stored on ByteIT servers and can be retrieved using `get_job_result()`.

---

#### `S3OutputConnector`
Store processed results directly to AWS S3 buckets.

```python
from byteit.connectors import S3OutputConnector

connector = S3OutputConnector(
    bucket="my-results-bucket",
    key="processed/result.txt",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"  # Optional
)
```

**Parameters:**
- `bucket` (str): S3 bucket name for results
- `key` (str): S3 object key (file path in bucket) for the result
- `aws_access_key_id` (Optional[str]): AWS access key (uses boto3 defaults if not provided)
- `aws_secret_access_key` (Optional[str]): AWS secret key (uses boto3 defaults if not provided)
- `region` (Optional[str]): AWS region (uses boto3 defaults if not provided)

**Requirements:**
- Install boto3: `pip install boto3`
- Server-side support for S3 output connectors

**Raises:**
- `ImportError`: If boto3 is not installed

**Note:** The server-side implementation must support S3 output connectors. Check API documentation for availability.

## Adding New Connectors

Each connector should be in its own file named after the class (e.g., `MyConnector.py`).

### Input Connector Example

1. Create a new file `MyInputConnector.py`:

```python
from typing import Any, Dict, Tuple
from .base import InputConnector

class MyInputConnector(InputConnector):
    """Description of your connector."""
    
    def __init__(self, custom_params):
        """Initialize the connector."""
        self.custom_params = custom_params
    
    def get_file_data(self) -> Tuple[str, Any]:
        """
        Implement file retrieval logic.
        
        Returns:
            Tuple of (filename, file_object)
        """
        filename = "file.pdf"
        file_object = self._fetch_file()
        return (filename, file_object)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary with connector type and configuration
        """
        return {
            "type": "my_connector",
            "params": self.custom_params
        }
```

2. Export it in `__init__.py`:

```python
from .MyInputConnector import MyInputConnector

__all__ = [
    # ... other exports
    "MyInputConnector",
]
```

### Output Connector Example

1. Create a new file `MyOutputConnector.py`:

```python
from typing import Any, Dict
from .base import OutputConnector

class MyOutputConnector(OutputConnector):
    """Description of your output connector."""
    
    def __init__(self, destination):
        """Initialize the connector."""
        self.destination = destination
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary with connector type and configuration
        """
        return {
            "type": "my_output",
            "destination": self.destination
        }
```

2. Export it in `__init__.py`:

```python
from .MyOutputConnector import MyOutputConnector

__all__ = [
    # ... other exports
    "MyOutputConnector",
]
```

## Planned Future Connectors

Additional connectors that could be implemented:

### Input Connectors
- **GoogleDriveInputConnector**: Download from Google Drive
- **AzureBlobInputConnector**: Download from Azure Blob Storage
- **URLInputConnector**: Download from HTTP/HTTPS URLs
- **DropboxInputConnector**: Download from Dropbox
- **FTPInputConnector**: Download from FTP/SFTP servers

### Output Connectors
- **GoogleDriveOutputConnector**: Save to Google Drive
- **AzureBlobOutputConnector**: Save to Azure Blob Storage
- **WebhookOutputConnector**: POST results to webhooks
- **DropboxOutputConnector**: Save to Dropbox
- **FTPOutputConnector**: Upload to FTP/SFTP servers

## Testing

Test your connector implementations by adding tests to `tests/test_connectors.py`.

Example:
```python
def test_local_file_connector():
    """Test LocalFileInputConnector."""
    connector = LocalFileInputConnector("test_file.pdf")
    
    # Test to_dict
    config = connector.to_dict()
    assert config["type"] == "local_file"
    assert config["file_type"] == "pdf"
    
    # Test get_file_data
    filename, file_obj = connector.get_file_data()
    assert filename == "test_file.pdf"
    assert file_obj is not None


def test_s3_input_connector():
    """Test S3InputConnector."""
    connector = S3InputConnector(
        bucket="test-bucket",
        key="documents/test.pdf",
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret"
    )
    
    # Test to_dict
    config = connector.to_dict()
    assert config["type"] == "s3_input"
    assert config["bucket"] == "test-bucket"
    assert config["key"] == "documents/test.pdf"
```

## Usage Examples

### Process a file from local filesystem

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

client = ByteITClient(api_key="your-api-key")
input_connector = LocalFileInputConnector("document.pdf")

result = client.process_document(
    input_connector=input_connector,
    output_path="result.txt"
)
```

### Process a file from AWS S3

```python
from byteit import ByteITClient
from byteit.connectors import S3InputConnector

client = ByteITClient(api_key="your-api-key")

input_connector = S3InputConnector(
    bucket="my-documents",
    key="invoices/invoice-2024.pdf",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"
)

result = client.process_document(
    input_connector=input_connector,
    output_path="invoice_text.txt"
)
```

### Save results to AWS S3

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector, S3OutputConnector

client = ByteITClient(api_key="your-api-key")

input_connector = LocalFileInputConnector("document.pdf")
output_connector = S3OutputConnector(
    bucket="my-results",
    key="processed/document-result.txt",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"
)

result = client.process_document(
    input_connector=input_connector,
    output_connector=output_connector
)
```

### S3 to S3 processing

```python
from byteit import ByteITClient
from byteit.connectors import S3InputConnector, S3OutputConnector

client = ByteITClient(api_key="your-api-key")

# Read from one S3 bucket
input_connector = S3InputConnector(
    bucket="input-documents",
    key="raw/document.pdf",
    region="us-east-1"
)

# Write to another S3 bucket
output_connector = S3OutputConnector(
    bucket="processed-documents",
    key="processed/document.txt",
    region="us-east-1"
)

result = client.process_document(
    input_connector=input_connector,
    output_connector=output_connector
)
```
