# ByteIT Library Examples

This directory contains example scripts demonstrating how to use the ByteIT library for document processing.

## Prerequisites

1. **Install the ByteIT library:**
   ```bash
   cd ..
   pip install -e .
   ```

2. **Get your API key:**
   - Visit [https://byteit.ai/dashboard/api-keys](https://byteit.ai/dashboard/api-keys)
   - Create an API key if you don't have one

3. **Set your API key as an environment variable:**
   ```bash
   export BYTEIT_API_KEY='your-api-key-here'
   ```

## Examples

### 1. Simple Example (`simple_example.py`)

The easiest way to get started. Processes a single document with minimal code.

**Usage:**
```bash
python simple_example.py path/to/your/document.pdf
```

**What it does:**
- Takes a local file path as input
- Processes the document using ByteIT service
- Saves the result in Markdown format
- Shows a preview of the output

### 2. Comprehensive Examples (`local_file_processing.py`)

Interactive script with multiple examples covering all library features.

**Usage:**
```bash
python local_file_processing.py
```

**Examples included:**

1. **Basic Processing** - Process a document with default settings
2. **Custom Options** - Use custom processing options (OCR model, languages, page range, output format)
3. **Context Manager** - Proper resource management using `with` statement
4. **List Jobs** - View all your processing jobs
5. **Check Job Status** - Monitor a specific job's progress

### 3. Batch Processing (`batch_processing.py`)

Process multiple documents efficiently.

**Usage:**
```bash
python batch_processing.py
```

**What it does:**
- Processes multiple documents in sequence or parallel
- Demonstrates error handling for batch operations
- Shows progress tracking

### 4. AWS S3 Integration (`s3_example.py`)

Examples of using ByteIT with AWS S3 for input and output.

**Prerequisites:**
```bash
pip install boto3
export AWS_ACCESS_KEY_ID='your-access-key'
export AWS_SECRET_ACCESS_KEY='your-secret-key'
export AWS_REGION='us-east-1'  # Optional
```

**Usage:**
```bash
python s3_example.py
```

**Examples included:**
1. **S3 Input** - Process files directly from S3 buckets
2. **S3 Output** - Save processed results to S3 buckets
3. **S3 to S3** - Complete S3 workflow (read from S3, process, save to S3)

**Note:** Edit the script to replace bucket names and keys with your own values.

## Common Use Cases

### Process a PDF to Markdown
```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = LocalFileInputConnector("document.pdf")
    
    result = client.process_document(
        input_connector=input_connector,
        processing_options={"output_format": "md"},
        output_path="output.md"
    )
    print(f"Saved to: {result}")
```

### Process with Custom Options
```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = LocalFileInputConnector("document.pdf")
    
    options = {
        "output_format": "json",
        "ocr_model": "tesseractocr",
        "languages": ["eng", "deu"],
        "page_range": "1-10"
    }
    
    result = client.process_document(
        input_connector=input_connector,
        processing_options=options,
        output_path="output.json"
    )
```

### Process from AWS S3
```python
from byteit import ByteITClient
from byteit.connectors import S3InputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = S3InputConnector(
        bucket="my-documents",
        key="invoices/invoice.pdf",
        aws_access_key_id="YOUR_ACCESS_KEY",
        aws_secret_access_key="YOUR_SECRET_KEY",
        region="us-east-1"
    )
    
    result = client.process_document(
        input_connector=input_connector,
        output_path="result.txt"
    )
```

### Save Results to AWS S3
```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector, S3OutputConnector

with ByteITClient(api_key="your-api-key") as client:
    input_connector = LocalFileInputConnector("document.pdf")
    output_connector = S3OutputConnector(
        bucket="my-results",
        key="processed/result.txt",
        aws_access_key_id="YOUR_ACCESS_KEY",
        aws_secret_access_key="YOUR_SECRET_KEY",
        region="us-east-1"
    )
    
    result = client.process_document(
        input_connector=input_connector,
        output_connector=output_connector
    )
```

### Async Processing (Create Job and Check Later)
```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

client = ByteITClient(api_key="your-api-key")

# Create job
input_connector = LocalFileInputConnector("large_document.pdf")
job = client.create_job(input_connector=input_connector)
print(f"Job ID: {job.id}")

# Later, check status
job = client.get_job(job.id)
if job.is_completed:
    result = client.get_job_result(job.id, output_path="result.txt")
    print(f"Result saved to: {result}")
elif job.is_failed:
    print(f"Job failed: {job.processing_error}")
else:
    print(f"Job status: {job.processing_status}")
```

### List All Jobs
```python
from byteit import ByteITClient

with ByteITClient(api_key="your-api-key") as client:
    job_list = client.list_jobs()
    
    for job in job_list.jobs:
        print(f"{job.id}: {job.processing_status}")
        if job.metadata:
            print(f"  File: {job.metadata.original_filename}")
```

## Available Processing Options

| Option | Description | Example Values |
|--------|-------------|----------------|
| `output_format` | Output format | `"txt"`, `"md"`, `"json"`, `"html"` |
| `ocr_model` | OCR engine to use | `"tesseractocr"`, etc. |
| `languages` | Languages to process | `["eng"]`, `["eng", "deu"]` |
| `page_range` | Pages to process | `"1-5"`, `"all"` |

## Connectors

### Input Connectors

**LocalFileInputConnector** - Process files from your local filesystem

```python
from byteit.connectors import LocalFileInputConnector

# Automatic file type detection
input_connector = LocalFileInputConnector("document.pdf")
```

**S3InputConnector** - Process files from AWS S3

```python
from byteit.connectors import S3InputConnector

input_connector = S3InputConnector(
    bucket="my-bucket",
    key="documents/file.pdf",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"  # Optional
)
```

### Output Connectors

**ByteITStorageOutputConnector** - Store results in ByteIT cloud storage (default)

```python
from byteit.connectors import ByteITStorageOutputConnector

output_connector = ByteITStorageOutputConnector()
```

Results are stored on ByteIT servers and can be retrieved using `get_job_result()`.

**S3OutputConnector** - Store results in AWS S3

```python
from byteit.connectors import S3OutputConnector

output_connector = S3OutputConnector(
    bucket="my-results",
    key="processed/result.txt",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    region="us-east-1"  # Optional
)
```

## Error Handling

The library provides specific exception types for different error scenarios:

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector
from byteit.exceptions import (
    APIKeyError,
    AuthenticationError,
    ValidationError,
    JobProcessingError,
    NetworkError,
)

try:
    client = ByteITClient(api_key="your-api-key")
    input_connector = LocalFileInputConnector("document.pdf")
    result = client.process_document(input_connector)
    
except APIKeyError as e:
    print(f"Invalid API key: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ValidationError as e:
    print(f"Invalid request: {e}")
except JobProcessingError as e:
    print(f"Processing failed: {e}")
except NetworkError as e:
    print(f"Network error: {e}")
```

## Need Help?

- **Documentation:** [https://docs.byteit.ai](https://docs.byteit.ai)
- **Support:** support@byteit.ai
- **GitHub:** [https://github.com/byteit-ai/byteit-library](https://github.com/byteit-ai/byteit-library)

## Tips

1. Use the context manager (`with ByteITClient(...) as client:`) for automatic cleanup
2. For large files, consider using async processing with `create_job()` instead of `process_document()`
3. Set appropriate `max_wait_time` based on your document size
4. Check job status before downloading results to avoid unnecessary API calls
5. Handle exceptions appropriately in production code
6. For S3 operations, consider using IAM roles instead of hardcoded credentials
