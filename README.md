# ByteIT Python Client Library

A Python client library for the ByteIT text extraction service. Extract text from documents (PDF, DOCX, images, etc.) with ease using a flexible connector-based architecture.

## Installation

```bash
pip install byteit
```

## Quick Start

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

# Initialize the client with your API key
client = ByteITClient(api_key="your-api-key-here")

# Create an input connector for your local file
input_connector = LocalFileInputConnector("sample_document.pdf")

# Process the document
result = client.process_document(
    input_connector=input_connector,
    processing_options={"output_format": "md"},
    output_path="output.md"
)
print(f"Document processed and saved to: {result}")
```

## Features

- 🚀 Simple and intuitive API with connector-based architecture
- 📄 Support for multiple document formats (PDF, DOCX, images, etc.)
- 🔌 Flexible input/output connectors for different storage backends
- 🔥 **Batch processing with concurrent/async support** for multiple documents
- ⏱️ Automatic polling for job completion
- 🔄 Built-in retry logic with exponential backoff
- 🎯 Type hints for better IDE support
- 🛡️ Comprehensive error handling
- 📦 Context manager support for automatic resource cleanup

## Usage Examples

### Basic Usage with Connectors

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector, ByteITStorageOutputConnector

# Create client
client = ByteITClient(api_key="your-api-key")

# Create input connector for local file
input_connector = LocalFileInputConnector("document.pdf")

# Create output connector (stores result in ByteIT cloud storage)
# Output connectors are optional, if not provided the files will be temporarily held in ByteIT cloud storage, according to our Terms Of Service.
output_connector = ByteITStorageOutputConnector() #Add the ByteITStorageOutputConnector for long term storage

# Create a job
job = client.create_job(
    input_connector=input_connector,
    output_connector=output_connector,
)

# Wait for processing to complete
completed_job = client.wait_for_job(job.id)

# Download the result
result = client.get_job_result(job.id, output_path="output.txt")
```

### One-Step Processing

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = LocalFileInputConnector("document.pdf")
    
    # Process document in one call
    result = client.process_document(
        input_connector=input_connector,
        processing_options={"output_format": "md"},
        output_path="output.md"
    )
    print(f"Result saved to: {result}")
```

### Using Context Manager

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = LocalFileInputConnector("document.pdf")
    result_path = client.process_document(
        input_connector=input_connector,
        output_path="output.txt"
    )
    print(f"Saved to: {result_path}")
```

### Batch Processing (Multiple Files)

Process multiple documents concurrently with async/threaded processing:

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

with ByteITClient(api_key="your-api-key") as client:
    # Create input connectors for multiple files
    input_connectors = [
        LocalFileInputConnector("document1.pdf"),
        LocalFileInputConnector("document2.pdf"),
        LocalFileInputConnector("document3.pdf"),
    ]
    
    # Option 1: Create multiple jobs at once (async)
    jobs = client.create_job(input_connectors)
    print(f"Created {len(jobs)} jobs")
    
    # Option 2: Process all documents end-to-end (async)
    output_paths = ["output1.txt", "output2.txt", "output3.txt"]
    results = client.process_document(
        input_connector=input_connectors,
        output_path=output_paths,
        max_workers=3  # Process up to 3 documents concurrently
    )
    print(f"Processed {len(results)} documents")
```

**Features:**
- Accepts either a single connector or a list of connectors
- Automatically uses concurrent processing for multiple files
- Returns a single result or list of results to match input
- Configurable concurrency with `max_workers` parameter
- Automatic retry logic for database lock errors (SQLite development environments)

**Important Note for Development/Testing:**
If you're testing against a local SQLite database, you may encounter "database is locked" errors when processing multiple files concurrently. This is a SQLite limitation (file-level locking). Use `max_workers=1` to process files sequentially:

```python
# For SQLite backend (development)
jobs = client.create_job(input_connectors, max_workers=1)

# Production PostgreSQL databases handle concurrent requests without issues
jobs = client.create_job(input_connectors, max_workers=5)  # Default
```

### List All Jobs

```python
job_list = client.list_jobs()
print(f"Total jobs: {job_list.count}")

for job in job_list.jobs:
    print(f"Job {job.id}: {job.processing_status}")
```

### Check Job Status

```python
job = client.get_job("job-id-here")
print(f"Status: {job.processing_status}")
print(f"Completed: {job.is_completed}")
print(f"Failed: {job.is_failed}")
```

### Custom Processing Options

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = LocalFileInputConnector("document.pdf")
    
    processing_options = {
        "output_format": "md",  # Output in Markdown format
        "ocr_model": "tesseractocr",  # OCR engine
        "languages": ["eng", "deu"],  # English and German
        "page_range": "1-10"  # Only first 10 pages
    }
    
    result = client.process_document(
        input_connector=input_connector,
        processing_options=processing_options,
        output_path="output.md"
    )
```

### AWS S3 Integration

**Process files from S3:**

```python
from byteit import ByteITClient
from byteit.connectors import S3InputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = S3InputConnector(
        bucket="my-documents",
        key="invoices/invoice-2024.pdf",
        aws_access_key_id="YOUR_ACCESS_KEY",
        aws_secret_access_key="YOUR_SECRET_KEY",
        region="us-east-1"
    )
    
    result = client.process_document(
        input_connector=input_connector,
        processing_options={"output_format": "txt"},
        output_path="invoice_text.txt"
    )
```

**Save results to S3:**

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector, S3OutputConnector

with ByteITClient(api_key="your-api-key") as client:
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

**S3 to S3 processing:**

```python
from byteit import ByteITClient
from byteit.connectors import S3InputConnector, S3OutputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = S3InputConnector(
        bucket="input-documents",
        key="raw/document.pdf",
        region="us-east-1"
    )
    
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

### Error Handling

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector
from byteit.exceptions import (
    APIKeyError,
    AuthenticationError,
    JobProcessingError,
    ValidationError
)

try:
    client = ByteITClient(api_key="your-api-key")
    input_connector = LocalFileInputConnector("document.pdf")
    
    result = client.process_document(
        input_connector=input_connector,
        output_path="output.txt"
    )
except APIKeyError as e:
    print(f"Invalid API key: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ValidationError as e:
    print(f"Invalid request: {e}")
except JobProcessingError as e:
    print(f"Processing failed: {e}")
finally:
    client.close()
```

## Configuration

### Client Initialization

```python
from byteit import ByteITClient

client = ByteITClient(api_key="your-api-key")
```

### Input Connectors

The library uses connectors to provide flexible input sources:

**LocalFileInputConnector** - Read files from local filesystem:

```python
from byteit.connectors import LocalFileInputConnector

# Automatic file type detection from extension
input_connector = LocalFileInputConnector("document.pdf")

# Explicit file type specification
input_connector = LocalFileInputConnector("document.xyz", file_type="pdf")
```

**S3InputConnector** - Download files from AWS S3:

```python
from byteit.connectors import S3InputConnector

# Process a file from S3
input_connector = S3InputConnector(
    bucket="my-documents",
    key="invoices/invoice.pdf",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"  # Optional
)
```

**Note:** Requires `boto3` package: `pip install boto3`

### Output Connectors

**ByteITStorageOutputConnector** - Store results in ByteIT cloud storage (default):

```python
from byteit.connectors import ByteITStorageOutputConnector

output_connector = ByteITStorageOutputConnector()
```

Results are stored on ByteIT servers and can be retrieved using `get_job_result()`.

**S3OutputConnector** - Save results directly to AWS S3:

```python
from byteit.connectors import S3OutputConnector

# Save results to S3
output_connector = S3OutputConnector(
    bucket="my-results",
    key="processed/result.txt",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"  # Optional
)
```

**Note:** Requires `boto3` package: `pip install boto3`. Server-side support required.

### Processing Options

```python
processing_options = {
    "output_format": "md",  # Output format: txt, md, json, html
    "ocr_model": "tesseractocr",  # OCR engine
    "languages": ["eng", "deu"],  # Language codes
    "page_range": "1-10"  # Page range to process
}

client.process_document(
    input_connector=input_connector,
    processing_options=processing_options,
    output_path="output.md",
    poll_interval=5,  # Poll every 5 seconds
    max_wait_time=600  # Wait up to 10 minutes
)
```

## API Reference

### ByteITClient

The main client class for interacting with the ByteIT API.

#### Methods

- `create_job(input_connector, output_connector=None, processing_options=None, timeout=30, max_workers=5)` - Create one or more processing jobs
  - **Single file:** `create_job(connector) -> Job`
  - **Multiple files:** `create_job([conn1, conn2, ...]) -> List[Job]` (async)
- `get_job(job_id, timeout=30)` - Get job status and information
- `list_jobs(timeout=30)` - List all jobs for the authenticated user
- `get_job_result(job_id, output_path=None, timeout=30)` - Download processed result
- `wait_for_job(job_id, poll_interval=5, max_wait_time=600, timeout=30)` - Wait for job completion
- `process_document(input_connector, output_connector=None, processing_options=None, output_path=None, poll_interval=5, max_wait_time=600, timeout=30, max_workers=5)` - Convenience method for end-to-end processing
  - **Single file:** `process_document(connector) -> bytes | str`
  - **Multiple files:** `process_document([conn1, conn2, ...]) -> List[bytes | str]` (async)
- `close()` - Close the HTTP session

**Batch Processing:**
Both `create_job()` and `process_document()` support batch processing by accepting a list of input connectors.
When multiple connectors are provided, jobs are created and processed concurrently using ThreadPoolExecutor.
The `max_workers` parameter controls the level of concurrency (default: 5).

### Connectors

#### InputConnector (Base Class)

Base class for all input connectors.

**LocalFileInputConnector** - Read files from local filesystem:

```python
from byteit.connectors import LocalFileInputConnector

connector = LocalFileInputConnector(file_path="document.pdf", file_type="pdf")
```

**Properties:**
- `file_path` (str) - Path to the local file
- `file_type` (Optional[str]) - File type override (auto-detected if not provided)

**S3InputConnector** - Download files from AWS S3:

```python
from byteit.connectors import S3InputConnector

connector = S3InputConnector(
    bucket="my-bucket",
    key="documents/file.pdf",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"
)
```

**Properties:**
- `bucket` (str) - S3 bucket name
- `key` (str) - S3 object key
- `aws_access_key_id` (Optional[str]) - AWS access key
- `aws_secret_access_key` (Optional[str]) - AWS secret key
- `region` (Optional[str]) - AWS region
- `file_type` (Optional[str]) - File type override

**Requirements:** `pip install boto3`

#### OutputConnector (Base Class)

Base class for all output connectors.

**ByteITStorageOutputConnector** - Store in ByteIT cloud storage:

```python
from byteit.connectors import ByteITStorageOutputConnector

connector = ByteITStorageOutputConnector()
```

**S3OutputConnector** - Save results to AWS S3:

```python
from byteit.connectors import S3OutputConnector

connector = S3OutputConnector(
    bucket="my-results",
    key="processed/result.txt",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"
)
```

**Properties:**
- `bucket` (str) - S3 bucket name
- `key` (str) - S3 object key for result
- `aws_access_key_id` (Optional[str]) - AWS access key
- `aws_secret_access_key` (Optional[str]) - AWS secret key
- `region` (Optional[str]) - AWS region

**Requirements:** `pip install boto3` (server-side support required)

### Models

#### Job

Represents a document processing job.

**Properties:**
- `id` - Job identifier
- `processing_status` - Current status (pending, processing, completed, failed)
- `processing_error` - Error message if job failed
- `created_at` - Job creation timestamp
- `metadata` - Job metadata including original filename
- `is_completed` - Boolean indicating if job is complete
- `is_failed` - Boolean indicating if job failed
- `is_processing` - Boolean indicating if job is in progress

#### JobList

List of jobs with metadata.

**Properties:**
- `jobs` - List of Job objects
- `count` - Total number of jobs
- `detail` - Optional detail message

### Exceptions

All exceptions inherit from `ByteITError`:

- `APIKeyError` - Invalid or missing API key
- `AuthenticationError` - Authentication failed
- `ValidationError` - Request validation error
- `ResourceNotFoundError` - Resource not found
- `RateLimitError` - Rate limit exceeded
- `ServerError` - Server-side error
- `NetworkError` - Network connectivity error
- `JobProcessingError` - Job processing error

## Getting an API Key

1. Visit [https://byteit.ai/dashboard/api-keys](https://byteit.ai/dashboard/api-keys)
2. Sign up or log in to your account
3. Generate a new API key
4. Copy the key and set it as an environment variable:
   ```bash
   export BYTEIT_API_KEY='your-api-key-here'
   ```

## Requirements

### Core Dependencies

- Python 3.8+
- requests >= 2.31.0
- typing-extensions >= 4.5.0

### Optional Dependencies

For AWS S3 connector support:
```bash
pip install boto3
```

## Installation

**Basic installation:**
```bash
pip install byteit
```

**With S3 support:**
```bash
pip install byteit boto3
```

## Examples

Check out the `examples/` directory for complete examples:

- `simple_example.py` - Basic document processing
- `local_file_processing.py` - Comprehensive examples with all features
- `batch_processing_example.py` - Process multiple documents concurrently
- `s3_example.py` - AWS S3 integration examples

## Troubleshooting

### Database Lock Errors (SQLite Development)

**Problem:** When batch processing multiple files, you get errors like:
```
{"error":"Unexpected error sending SQS message: database is locked"}
```

**Cause:** This is a SQLite limitation. SQLite uses file-level locking and cannot handle concurrent write operations from multiple threads. This only affects local development environments using SQLite.

**Solutions:**

1. **Sequential Processing (Recommended for SQLite):**
   ```python
   # Process files one at a time
   jobs = client.create_job(input_connectors, max_workers=1)
   ```

2. **The library includes automatic retry logic** with exponential backoff that will handle transient lock errors.

3. **Use PostgreSQL in Production:** PostgreSQL supports true concurrent connections and won't have this issue. The production ByteIT API uses PostgreSQL.

**When this matters:**
- ✅ Testing locally against SQLite database → Use `max_workers=1`
- ❌ Production API (PostgreSQL) → No issue, use default `max_workers=5` or higher

### Network Timeouts

If processing large documents, you may need to increase timeout values:

```python
result = client.process_document(
    input_connector=connector,
    timeout=60,  # Increase request timeout
    max_wait_time=1200  # Wait up to 20 minutes for processing
)
```

## License

Proprietary License - Free to use but redistribution is prohibited. See [LICENSE](LICENSE) file for details.

## Support

- **Documentation:** [https://docs.byteit.ai](https://docs.byteit.ai)
- **Email:** support@byteit.ai
- **Issues:** [GitHub Issues](https://github.com/byteit-ai/byteit-library/issues)
- **Repository:** [https://github.com/byteit-ai/byteit-library](https://github.com/byteit-ai/byteit-library)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
