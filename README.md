# ByteIT Python Client Library

A Python client library for the ByteIT text extraction service. Extract text from documents (PDF, DOCX, images, etc.) with ease.

## Installation

```bash
pip install byteit
```

## Quick Start

```python
from byteit import ByteITClient

# Initialize the client with your API key
client = ByteITClient(api_key="your-api-key-here")

# Process a document (one-liner)
result = client.process_document("document.pdf", file_type="pdf", output_path="output.md")
print(f"Document processed and saved to: {result}")
```

## Features

- 🚀 Simple and intuitive API
- 📄 Support for multiple document formats (PDF, DOCX, images, etc.)
- ⏱️ Automatic polling for job completion
- 🔄 Built-in retry logic with exponential backoff
- 🎯 Type hints for better IDE support
- 🛡️ Comprehensive error handling
- 📦 Context manager support

## Usage Examples

### Basic Usage

```python
from byteit import ByteITClient

# Create client
client = ByteITClient(api_key="your-api-key")

# Upload and process a document
with open("document.pdf", "rb") as f:
    job = client.create_job(f, file_type="pdf")

# Wait for processing to complete
completed_job = client.wait_for_job(job.id)

# Download the result
result = client.get_job_result(job.id, output_path="output.md")
```

### One-Step Processing

```python
# Process document in one call
result = client.process_document(
    "document.pdf",
    file_type="pdf",
    output_format="markdown",
    output_path="output.md"
)
```

### Using Context Manager

```python
with ByteITClient(api_key="your-api-key") as client:
    result = client.process_document("document.pdf", "pdf")
    print(result.decode("utf-8"))
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
processing_options = {
    "ocr_enabled": True,
    "language": "en",
    "extract_tables": True
}

job = client.create_job(
    "document.pdf",
    file_type="pdf",
    processing_options=processing_options
)
```

### Error Handling

```python
from byteit import ByteITClient, APIKeyError, JobProcessingError

try:
    client = ByteITClient(api_key="your-api-key")
    result = client.process_document("document.pdf", "pdf")
except APIKeyError as e:
    print(f"Authentication failed: {e.message}")
except JobProcessingError as e:
    print(f"Processing failed: {e.message}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Configuration

### Client Options

```python
client = ByteITClient(
    api_key="your-api-key",
    base_url="https://api.byteit.ai",  # Optional: custom API URL
    timeout=30,                         # Request timeout in seconds
    max_retries=3                       # Maximum retry attempts
)
```

### Processing Options

```python
client.process_document(
    "document.pdf",
    file_type="pdf",
    output_format="markdown",           # Output format
    poll_interval=5,                    # Poll every 5 seconds
    max_wait_time=600                   # Wait up to 10 minutes
)
```

## API Reference

### ByteITClient

The main client class for interacting with the ByteIT API.

#### Methods

- `create_job(file, file_type, output_format="markdown", processing_options=None)` - Create a new processing job
- `get_job(job_id)` - Get job status and information
- `list_jobs(user_id=None)` - List all jobs for the user
- `get_job_result(job_id, output_path=None)` - Download processed result
- `wait_for_job(job_id, poll_interval=5, max_wait_time=600)` - Wait for job completion
- `process_document(file, file_type, ...)` - Convenience method for end-to-end processing

### Models

#### Job

Represents a document processing job.

**Properties:**
- `id` - Job identifier
- `processing_status` - Current status (pending, processing, completed, failed)
- `created_at` - Job creation timestamp
- `is_completed` - Boolean indicating if job is complete
- `is_failed` - Boolean indicating if job failed
- `is_processing` - Boolean indicating if job is in progress

#### JobList

List of jobs with metadata.

**Properties:**
- `jobs` - List of Job objects
- `count` - Total number of jobs

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

1. Sign up at [https://byteit.ai](https://byteit.ai)
2. Navigate to your account settings
3. Generate a new API key
4. Copy the key (format: `<id>.<secret>`)

## Requirements

- Python 3.8+
- requests >= 2.31.0

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: [https://docs.byteit.ai](https://docs.byteit.ai)
- Issues: [GitHub Issues](https://github.com/byteit-ai/byteit-library/issues)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
