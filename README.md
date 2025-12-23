# ByteIT Python Library User Guide

This guide provides a complete overview of the ByteIT Python library for document text extraction. It covers installation, setup, connectors, API methods, and examples.

## What is ByteIT?

ByteIT is a Python client library for the ByteIT text extraction service. It allows you to process documents (PDFs, images, etc.) by uploading them locally or from cloud storage like S3, and retrieve extracted text in various formats.

## Installation

Install the library using pip:

```bash
pip install byteit
```

Or from source:

```bash
git clone https://github.com/byteit-ai/byteit-library.git
cd byteit-library
pip install -e .
```

Dependencies include [`requests`](venv/lib/python3.12/site-packages/requests/__init__.py ) and [`typing-extensions`](/usr/lib/python3.12/typing.py ).

## Getting Started

### API Key Setup

You need a ByteIT API key to access the service.
If you have not generated your API key yet, please do so through the ByteIT website or email support for assistance.

### Initializing the Client

Import and initialize the client:

```python
from byteit import ByteITClient

client = ByteITClient(api_key="your-api-key-here")
```

Use the client as a context manager for automatic cleanup:

```python
with ByteITClient(api_key="your-api-key-here") as client:
    # Your code here
    pass
```

## Connectors

Connectors handle input (source of documents) and output (destination for results).

### Input Connectors

#### LocalFileInputConnector

Uploads a local file for processing.

- **Parameters**:
  - [`file_path`](byteit/connectors/LocalFileInputConnector.py ) (str): Path to the local file (required).

- **Example**:
  ```python
  from byteit.connectors import LocalFileInputConnector

  input_connector = LocalFileInputConnector(file_path="sample_document.pdf")
  ```

#### S3InputConnector

Fetches files directly from Amazon S3 using IAM role authentication. The file does not pass through your local machine.

- **Prerequisites**: Configure an AWS IAM role in your ByteIT dashboard.
- **Parameters**:
  - [`source_bucket`](byteit/connectors/S3InputConnector.py ) (str): S3 bucket name (required).
  - [`source_path_inside_bucket`](byteit/connectors/S3InputConnector.py ) (str): Path to the file within the bucket (required).

- **Example**:
  ```python
  from byteit.connectors import S3InputConnector

  input_connector = S3InputConnector(
      source_bucket="your-bucket",
      source_path_inside_bucket="path/to/file.pdf"
  )
  ```

### Output Connectors

#### ByteITStorageOutputConnector (Default)

Stores results in ByteIT cloud storage. Retrieve later using job ID.

- **Parameters**: None (default connector).

- **Example**:
  ```python
  from byteit.connectors import ByteITStorageOutputConnector

  output_connector = ByteITStorageOutputConnector()
  ```

#### S3OutputConnector

Saves results directly to S3 using IAM role authentication. Results do not pass through your local machine.

- **Prerequisites**: Configure an AWS IAM role in your ByteIT dashboard.
- **Parameters**:
  - [`bucket`](byteit/connectors/S3OutputConnector.py ) (str): S3 bucket name (required).
  - [`path`](byteit/api_client.py ) (str): Path prefix within the bucket (optional, defaults to "").

- **Example**:
  ```python
  from byteit.connectors import S3OutputConnector

  output_connector = S3OutputConnector(bucket="your-bucket", path="results/")
  ```

## API Methods

All methods are part of [`ByteITClient`](byteit/api_client.py ).

### create_job

Creates one or more processing jobs.

- **Parameters**:
  - [`input_connector`](byteit/api_client.py ) (InputConnector or List[InputConnector]): Source connector(s) (required).
  - [`output_connector`](byteit/api_client.py ) (OutputConnector): Destination connector (optional, defaults to ByteITStorageOutputConnector).
  - [`processing_options`](byteit/api_client.py ) (ProcessingOptions): Processing settings (optional). Valid fields:
    - `languages` (List[str]): Languages to detect/process, e.g., ["en", "de"].
    - `page_range` (str): Page range to process, e.g., "1-5".
    - `output_format` (OutputFormat or str): Output format (txt, json, md, html). Sent as top-level parameter.
  - [`nickname`](byteit/api_client.py ) (str): Job nickname for identification (optional).
  - [`timeout`](byteit/api_client.py ) (int): Request timeout in seconds (optional, defaults to 30).
  - [`max_workers`](byteit/api_client.py ) (int): Concurrent workers for batch processing (optional, defaults to 5).

- **Returns**: Job or List[Job].
- **Raises**: ValidationError, APIKeyError, NetworkError, JobProcessingError.

- **Example**:
  ```python
  from byteit import ProcessingOptions, OutputFormat

  options = ProcessingOptions(
      languages=["en"],
      output_format=OutputFormat.TXT
  )
  job = client.create_job(
      input_connector=input_connector,
      processing_options=options
  )
  ```

### get_job

Retrieves job information.

- **Parameters**:
  - [`job_id`](byteit/api_client.py ) (str): Job ID (required).
  - [`timeout`](byteit/api_client.py ) (int): Request timeout (optional, defaults to 30).

- **Returns**: Job.
- **Raises**: ResourceNotFoundError, APIKeyError.

- **Example**:
  ```python
  job = client.get_job(job_id="job-123")
  ```

### list_jobs

Lists all jobs for the user.

- **Parameters**:
  - [`timeout`](byteit/api_client.py ) (int): Request timeout (optional, defaults to 30).

- **Returns**: JobList.
- **Raises**: APIKeyError.

- **Example**:
  ```python
  job_list = client.list_jobs()
  for job in job_list.jobs:
      print(job.id, job.processing_status)
  ```

### get_job_result

Downloads processed result.

- **Parameters**:
  - [`job_id`](byteit/api_client.py ) (str): Job ID (required).
  - [`output_path`](byteit/api_client.py ) (str or Path): Path to save result (optional).
  - [`timeout`](byteit/api_client.py ) (int): Request timeout (optional, defaults to 30).

- **Returns**: bytes or str (path if saved).
- **Raises**: ResourceNotFoundError, JobProcessingError.

- **Example**:
  ```python
  result = client.get_job_result(job_id="job-123", output_path="output.txt")
  ```

### wait_for_job

Polls until job completes.

- **Parameters**:
  - [`job_id`](byteit/api_client.py ) (str): Job ID (required).
  - [`poll_interval`](byteit/api_client.py ) (int): Seconds between checks (optional, defaults to 5).
  - [`max_wait_time`](byteit/api_client.py ) (int): Max wait time in seconds (optional, defaults to 600).
  - [`timeout`](byteit/api_client.py ) (int): Request timeout (optional, defaults to 30).

- **Returns**: Job.
- **Raises**: JobProcessingError.

- **Example**:
  ```python
  completed_job = client.wait_for_job(job_id="job-123")
  ```

### process_document

Convenience method: Creates job, waits, and retrieves result.

- **Parameters**:
  - [`input_connector`](byteit/api_client.py ) (InputConnector or List[InputConnector]): Source connector(s) (required).
  - [`output_connector`](byteit/api_client.py ) (OutputConnector): Destination connector (optional).
  - [`processing_options`](byteit/api_client.py ) (ProcessingOptions): Processing settings (optional).
  - [`nickname`](byteit/api_client.py ) (str): Job nickname (optional).
  - [`output_path`](byteit/api_client.py ) (str, Path, or List): Path(s) to save result(s) (optional).
  - [`poll_interval`](byteit/api_client.py ) (int): Poll interval (optional, defaults to 5).
  - [`max_wait_time`](byteit/api_client.py ) (int): Max wait time (optional, defaults to 600).
  - [`timeout`](byteit/api_client.py ) (int): Request timeout (optional, defaults to 30).
  - [`max_workers`](byteit/api_client.py ) (int): Concurrent workers (optional, defaults to 5).

- **Returns**: bytes, str, or List[bytes | str].
- **Raises**: ValidationError, APIKeyError, NetworkError, JobProcessingError.

- **Example**:
  ```python
  from byteit import ProcessingOptions, OutputFormat

  options = ProcessingOptions(output_format=OutputFormat.MD)
  result = client.process_document(
      input_connector=input_connector,
      processing_options=options,
      output_path="output.md"
  )
  ```

## Processing Options

Use the `ProcessingOptions` class to configure document processing:

```python
from byteit import ProcessingOptions, OutputFormat

options = ProcessingOptions(
    languages=["en", "de"],  # Languages to detect/process
    page_range="1-5",        # Page range to process (optional)
    output_format=OutputFormat.MD  # Output format (txt, md, json, html)
)
```

**Valid fields:**

- `languages` (List[str]): Languages to detect/process, e.g., ["en", "de"]. Default: ["en"].
- `page_range` (str): Page range to process, e.g., "1-5" or "all". Default: "" (all pages).
- `output_format` (OutputFormat or str): Output format. Valid values: "txt", "md", "json", "html". Default: "txt".

**Note:** The `output_format` is automatically extracted and sent as a top-level parameter to the API.

## Error Handling

Import exceptions from [`byteit.exceptions`](byteit/__init__.py ):

- [`ByteITError`](byteit/exceptions.py ): Base error.
- [`AuthenticationError`](byteit/exceptions.py ): Auth issues.
- [`ValidationError`](byteit/exceptions.py ): Invalid input.
- [`JobProcessingError`](byteit/exceptions.py ): Job failures.
- [`NetworkError`](byteit/exceptions.py ): Network issues.
- [`RateLimitError`](byteit/exceptions.py ): Rate limited.
- [`ServerError`](byteit/exceptions.py ): Server errors.
- [`ResourceNotFoundError`](byteit/exceptions.py ): Not found.

Example:

```python
from byteit.exceptions import ByteITError

try:
    job = client.create_job(input_connector)
except ByteITError as e:
    print(f"Error: {e}")
```

## Examples

See [`examples`](examples ) for full scripts.

### Basic Local File Processing

```python
from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector

client = ByteITClient(api_key="your-key")
input_conn = LocalFileInputConnector("sample_document.pdf")

result = client.process_document(input_conn, output_path="output.txt")
print(f"Result saved to: {result}")
```

### S3 to S3 Processing

```python
from byteit.connectors import S3InputConnector, S3OutputConnector

input_conn = S3InputConnector("bucket", "input/file.pdf")
output_conn = S3OutputConnector("bucket", "output/")

job = client.create_job(input_conn, output_conn)
client.wait_for_job(job.id)
```

### Batch Processing

```python
input_conns = [
    LocalFileInputConnector("doc1.pdf"),
    LocalFileInputConnector("doc2.pdf")
]

results = client.process_document(input_conns, output_path=["out1.txt", "out2.txt"])
```

## Best Practices

- Use context managers for client lifecycle.
- Validate inputs before processing.
- Handle exceptions appropriately.
- For batch jobs
- Follow PEP 8 and include docstrings/type hints as per Python instructions.

For more details, refer to the source code in [`byteit`](byteit ).
