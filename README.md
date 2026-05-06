# ByteIT Python SDK

ByteIT is a Python client for document parsing and structured extraction. Use it to submit files, retrieve parsed content, and extract schema-based data from completed parse jobs.

## Installation

```bash
pip install byteit
```

Requires Python 3.8+ and a ByteIT API key.

## Quick Start

```python
from byteit import ByteITClient

client = ByteITClient(api_key="your_api_key")
result = client.parse("document.pdf")
print(result.decode("utf-8"))
```

`parse()` returns raw bytes. Pass `output="result.json"` to write the result directly to disk.

## Parse Documents

```python
from byteit import ByteITClient, ProcessingOptions

client = ByteITClient(api_key="your_api_key")

result = client.parse(
    "invoice.pdf",
    processing_options=ProcessingOptions(languages=["en"], page_range="1-2"),
)
```

Public parse submission methods always request JSON output internally. If you need another format, request it when downloading an async result.

## Async Workflow

```python
job = client.parse_async("document.pdf")

status = client.get_job_status(job.id)
details = client.get_parse_job_details(job.id)

if status.is_completed:
    result_json = client.get_parse_job_result(job.id)
    result_txt = client.get_parse_job_result(job.id, result_format="txt")
```

Available parse-job methods:

| Method | Purpose |
|---|---|
| `get_parse_jobs()` | List parse jobs |
| `get_parse_job_details(job_id)` | Get full parse-job details |
| `get_job_status(job_id)` | Check lightweight processing status |
| `get_parse_job_result(job_id, result_format=None)` | Download parse result |

## Structured Extraction

Extraction runs on a completed parse job and returns a dictionary matching your schema.

```python
from byteit import ByteITClient, ExtractionSchema
from pydantic import Field


class InvoiceSchema(ExtractionSchema):
    invoice_number: str | None = Field(description="Invoice number")
    total_amount: str | None = Field(description="Total amount")


client = ByteITClient(api_key="your_api_key")
parse_job = client.parse_async("invoice.pdf")

result = client.extract(
    parse_job.id,
    InvoiceSchema,
    extraction_complexity="medium",
)
```

Async extraction is also available:

```python
extract_job = client.extract_async(parse_job.id, InvoiceSchema)

status = client.get_job_status(extract_job.id)
if status.is_completed:
    extracted = client.get_extract_job_result(extract_job.id)
```

Available extraction methods:

| Method | Purpose |
|---|---|
| `extract(parse_job_id, schema, output=None, extraction_complexity="medium")` | Run extraction and wait for the result |
| `extract_async(parse_job_id, schema, extraction_complexity="medium")` | Submit extraction without waiting |
| `get_extract_jobs()` | List extraction jobs |
| `get_extract_job_details(job_id)` | Get full extraction job details |
| `get_extract_job_result(job_id)` | Download extraction result |

## Processing Options

You can pass either a `ProcessingOptions` instance or a plain dictionary.

```python
result = client.parse(
    "document.pdf",
    processing_options={
        "languages": ["de", "en"],
        "page_range": "1-5",
        "extraction_type": "complex",
    },
)
```

## Error Handling

All SDK exceptions inherit from `ByteITError`.

```python
from byteit.exceptions import (
    AuthenticationError,
    ByteITError,
    JobProcessingError,
    RateLimitError,
    ValidationError,
)

try:
    result = client.parse("document.pdf")
except AuthenticationError:
    print("Invalid API key")
except ValidationError as exc:
    print("Invalid request:", exc.message)
except RateLimitError:
    print("Rate limit exceeded")
except JobProcessingError as exc:
    print("Processing failed:", exc.message)
except ByteITError as exc:
    print("ByteIT error:", exc.message)
```

## Supported Inputs

Common supported inputs include PDF, Word, PowerPoint, HTML, Markdown, plain text, JSON, XML, and common image formats such as PNG, JPEG, TIFF, and BMP.

## Notebook Behavior

When running in Jupyter, parse results are automatically displayed as JSON when possible. Pass `output=...` if you want to suppress inline display and save the response directly.

## Resources

- Studio: [studio.byteit.ai](https://studio.byteit.ai)
- Pricing: [byteit.ai/pricing](https://byteit.ai/pricing)
- Support: [byteit.ai/support](https://byteit.ai/support)
- LinkedIn: [ByteIT on LinkedIn](https://www.linkedin.com/company/byteit-ai)

Licensed under [Apache 2.0](LICENSE). © 2026 ByteIT GmbH.
