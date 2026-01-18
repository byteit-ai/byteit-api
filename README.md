# ByteIT API Library

**Turn your data into AI - Transform documents into structured data with a single line of code.**

ByteIT is an AI-powered document intelligence platform that extracts clean, structured data from PDFs, Word, Excel, and many other file formats. This Python SDK provides a simple, developer-first interface to ByteIT's advanced document processing capabilities.

---

## Why ByteIT?

- **Lightning Fast** - Process documents in under 2 seconds
- **AI-Powered** - Advanced ML models trained on millions of documents
- **Simple API** - Parse documents in one line: `client.parse("document.pdf")`
- **Developer First** - Clean code, full type hints, comprehensive SDKs
- **Enterprise Security** - End-to-end encryption and GDPR compliance
- **Smart Extraction** - Extract text, tables, forms, and structured data with AI precision

---

## Quick Start

### Installation

```bash
pip install byteit
```

### Basic Usage

```python
from byteit import ByteITClient

# Initialize client
client = ByteITClient(api_key="your_api_key")

# Parse a document
result = client.parse("invoice.pdf")
print(result.decode())
```

That's it. Your document is now structured text.

---

## Features

### Parse Any Document

```python
# Local files
result = client.parse("contract.pdf")

# Different formats
txt_result = client.parse("doc.pdf", output_format="txt")
json_result = client.parse("doc.pdf", output_format="json")
md_result = client.parse("doc.pdf", output_format="md")
html_result = client.parse("doc.pdf", output_format="html")

# Save to file
client.parse("doc.pdf", output="result.txt")
```

### S3 Integration

Process files directly from S3 without downloading - perfect for high-volume workflows:

```python
from byteit.connectors import S3InputConnector

# Parse from S3
result = client.parse(
    S3InputConnector(
        source_bucket="my-documents",
        source_path_inside_bucket="invoices/jan-2024.pdf"
    )
)
```

### Job Management

Track and retrieve processing jobs:

```python
# List all jobs
jobs = client.get_all_jobs()
for job in jobs:
    print(f"{job.id}: {job.processing_status}")

# Get specific job
job = client.get_job_by_id("job_123")

# Download result later
if job.is_completed:
    result = client.get_result(job.id)
```

### Context Manager

Automatic resource cleanup:

```python
with ByteITClient(api_key="your_key") as client:
    result = client.parse("document.pdf")
    # Session automatically closed
```

---

## API Reference

### ByteITClient

**`ByteITClient(api_key: str)`**

Initialize the ByteIT client.

**Parameters:**
- `api_key` (str): Your ByteIT API key

**Methods:**

#### `parse(input, output_format="txt", output=None)`

Parse a document and return the result.

**Parameters:**
- `input` (str | Path | InputConnector): File to parse
  - `str` or `Path`: Local file path
  - `S3InputConnector`: For S3 files
- `output_format` (str): Output format - "txt", "json", "md", or "html" (default: "txt")
- `output` (str | Path | None): Optional file path to save result

**Returns:** `bytes` - Parsed content

**Example:**
```python
result = client.parse("doc.pdf", output_format="json")
```

#### `get_all_jobs()`

Get all jobs for your account.

**Returns:** `List[Job]` - List of Job objects

#### `get_job_by_id(job_id: str)`

Get a specific job by ID.

**Parameters:**
- `job_id` (str): The job ID

**Returns:** `Job` - Job object

#### `get_result(job_id: str)`

Download result for a completed job.

**Parameters:**
- `job_id` (str): The job ID

**Returns:** `bytes` - Result content

---

## Connectors

### LocalFileInputConnector

Read files from local filesystem.

```python
from byteit.connectors import LocalFileInputConnector

connector = LocalFileInputConnector("path/to/file.pdf")
result = client.parse(connector)
```

### S3InputConnector

Read files from Amazon S3 using IAM role authentication - files never pass through your machine.

**Prerequisites:**
1. Contact [ByteIT support](https://byteit.ai/contact) to set up AWS connection
2. Provide IAM role ARN for ByteIT to assume
3. Grant role read access to your bucket

```python
from byteit.connectors import S3InputConnector

connector = S3InputConnector(
    source_bucket="my-bucket",
    source_path_inside_bucket="documents/file.pdf"
)
result = client.parse(connector)
```

---

## Error Handling

ByteIT SDK provides specific exceptions for different error scenarios:

```python
from byteit.exceptions import (
    APIKeyError,           # Invalid API key
    AuthenticationError,   # Authentication failed
    ValidationError,       # Invalid parameters
    ResourceNotFoundError, # Job/resource not found
    RateLimitError,        # Rate limit exceeded
    ServerError,           # Server-side error (5xx)
    JobProcessingError,    # Job processing failed
)

try:
    result = client.parse("document.pdf")
except ValidationError as e:
    print(f"Invalid input: {e.message}")
except RateLimitError:
    print("Rate limit exceeded - please wait")
except JobProcessingError as e:
    print(f"Processing failed: {e.message}")
```

All exceptions inherit from `ByteITError`:

```python
from byteit.exceptions import ByteITError

try:
    result = client.parse("document.pdf")
except ByteITError as e:
    print(f"ByteIT error: {e.message}")
    print(f"Status code: {e.status_code}")
    print(f"Response: {e.response}")
```

---

## Advanced Usage

### Batch Processing

Process multiple files efficiently:

```python
files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
results = []

for file in files:
    result = client.parse(file, output_format="json")
    results.append(result)
```

### Custom Output Paths

Organize results systematically:

```python
from pathlib import Path

input_dir = Path("inputs")
output_dir = Path("outputs")
output_dir.mkdir(exist_ok=True)

for pdf_file in input_dir.glob("*.pdf"):
    output_file = output_dir / f"{pdf_file.stem}.txt"
    client.parse(pdf_file, output=output_file)
```

### S3 Workflow

High-volume cloud processing:

```python
from byteit.connectors import S3InputConnector

# Process multiple S3 files
s3_files = [
    "invoices/2024-01.pdf",
    "invoices/2024-02.pdf",
    "invoices/2024-03.pdf",
]

for s3_path in s3_files:
    connector = S3InputConnector(
        source_bucket="my-documents",
        source_path_inside_bucket=s3_path
    )
    result = client.parse(connector, output_format="json")
    # Process result...
```

---

## Configuration

### Environment Variables

Set your API key via environment variable:

```bash
export BYTEIT_API_KEY="your_api_key_here"
```

```python
import os
from byteit import ByteITClient

client = ByteITClient(api_key=os.getenv("BYTEIT_API_KEY"))
```

### Custom Base URL

For testing or custom deployments:

```python
from byteit import ByteITClient

# Set custom URL (for development/testing)
ByteITClient.BASE_URL = "http://localhost:8000"
client = ByteITClient(api_key="test_key")
```

---

## Testing

The SDK includes comprehensive unit and integration tests.

### Run Unit Tests

```bash
pytest
```

### Run Integration Tests

Integration tests require a running ByteIT API and valid API key:

```bash
export BYTEIT_API_KEY="your_api_key"
pytest -m integration
```

### Run All Tests

```bash
pytest -m ""
```

---

## Requirements

- Python 3.8+
- `requests` library

---

## About ByteIT

ByteIT transforms unstructured documents into clean, structured data with AI-powered precision. Built for scale, designed for developers.

**Get started today:** [Start Processing Free](https://byteit.ai/pricing) - 1,000 free pages/month

---

## Support & Resources

- **Website:** [https://byteit.ai](https://byteit.ai)
- **Pricing:** [https://byteit.ai/pricing](https://byteit.ai/pricing)
- **Support:** [https://byteit.ai/support](https://byteit.ai/support)
- **Contact:** [https://byteit.ai/contact](https://byteit.ai/contact)
- **LinkedIn:** [ByteIT on LinkedIn](https://www.linkedin.com/company/byteit-ai)

---

## Legal

© 2026 ByteIT GmbH. All rights reserved.

- **Privacy Policy:** [https://byteit.ai/privacy-policy](https://byteit.ai/privacy-policy)
- **Terms of Service:** [https://byteit.ai/terms](https://byteit.ai/terms)
- **Impressum:** [https://byteit.ai/impressum](https://byteit.ai/impressum)

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.
