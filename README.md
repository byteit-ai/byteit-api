# ByteIT Python SDK

Python client for [ByteIT](https://byteit.ai) — AI-powered document parsing. Extract structured text from PDFs, Word files, images, and more with a single API call.

---

## Installation

```bash
pip install byteit
```

Requires Python 3.8+ and an API key from [byteit.ai](https://byteit.ai).

---

## Quick Start

```python
from byteit import ByteITClient, OutputFormat

client = ByteITClient(api_key="your_api_key")
result = client.parse("document.pdf")
print(result.decode())
```

Returns raw bytes. Pass `output="result.md"` to save directly to disk.

---

## Usage

### Parse and save

```python
# Returns bytes
result = client.parse("invoice.pdf", result_format=OutputFormat.JSON)

# Save to file
client.parse(
    "invoice.pdf",
    result_format=OutputFormat.MD,
    output="invoice.md",
)
```

**Output formats:** `OutputFormat.MD` *(default)*, `OutputFormat.TXT`,
`OutputFormat.JSON`, `OutputFormat.HTML`, `OutputFormat.EXCEL`

**Excel output note:** `OutputFormat.EXCEL` extracts tables into one or more Excel
files. Because a document can contain multiple tables, we returns the Excel
files bundled in a single `.zip` archive. If you pass the `output` parameter
with `result_format=OutputFormat.EXCEL`, the output path should end with `.zip`
instead of `.xlsx`.

### Async (non-blocking)

Submit a job and check back later — useful for large files or batch workflows.

```python
# Submit without waiting
job = client.parse_async("document.pdf")

# Poll status
status = client.get_job_status(job.id)
# status.processing_status: "pending" | "processing" | "completed" | "failed"

# Download when ready
if status.is_completed:
    result = client.get_job_result(job.id)
```

### Job management

```python
for job in client.get_jobs():
    print(f"{job.id}  {job.processing_status}  {job.result_format}")
```

### Processing options

```python
from byteit import ProcessingOptions

result = client.parse(
    "document.pdf",
    processing_options=ProcessingOptions(languages=["de", "en"], page_range="1-5"),
)
```

Or pass a plain dict:

```python
result = client.parse("doc.pdf", processing_options={"languages": ["de"]})
```

### API key from environment

```python
import os
client = ByteITClient(api_key=os.environ["BYTEIT_API_KEY"])
```

### Context manager

```python
with ByteITClient(api_key="your_key") as client:
    result = client.parse("doc.pdf")
```

---

## Supported File Types

| Documents | Images |
|-----------|--------|
| PDF `.pdf` | PNG `.png` |
| Word `.docx` | JPEG `.jpg` `.jpeg` |
| PowerPoint `.pptx` | TIFF `.tiff` |
| HTML `.html` | BMP `.bmp` |
| Markdown `.md` | |
| Plain text `.txt` | |
| JSON `.json` | |
| XML `.xml` | |

---

## Error Handling

All exceptions inherit from `ByteITError`.

```python
from byteit.exceptions import (
    AuthenticationError,
    ValidationError,
    RateLimitError,
    JobProcessingError,
    ByteITError,
)

try:
    result = client.parse("document.pdf")
except AuthenticationError:
    print("Invalid API key")
except ValidationError as e:
    print("Bad request:", e.message)
except RateLimitError:
    print("Rate limit hit — retry later")
except JobProcessingError as e:
    print("Processing failed:", e.message)
except ByteITError as e:
    print("Unexpected error:", e.message)
```

| Exception | When raised |
|---|---|
| `AuthenticationError` | Invalid or missing API key |
| `APIKeyError` | API key rejected (403) |
| `ValidationError` | Bad request parameters |
| `ResourceNotFoundError` | Job not found |
| `RateLimitError` | Rate limit exceeded |
| `JobProcessingError` | Job failed during processing |
| `ServerError` | Server-side error (5xx) |

---

## API Reference

### `ByteITClient(api_key)`

| Method | Description |
|---|---|
| `parse(input, ...)` | Parse a document, block until complete, return `bytes` |
| `parse_async(input, ...)` | Submit a job, return `Job` immediately |
| `get_job_status(job_id)` | Get current `Job` status |
| `get_job_result(job_id)` | Download result as `bytes` |
| `get_jobs()` | List all jobs as `list[Job]` |

#### `parse(input, output=None, processing_options=None, result_format=OutputFormat.MD) → bytes`

| Param | Type | Description |
|---|---|---|
| `input` | `str \| Path \| InputConnector` | File to parse |
| `output` | `str \| Path \| None` | Save result to disk (optional) |
| `processing_options` | `ProcessingOptions \| dict \| None` | Languages, page range, etc. |
| `result_format` | `OutputFormat` | `OutputFormat.MD`, `OutputFormat.TXT`, `OutputFormat.JSON`, `OutputFormat.HTML`, `OutputFormat.EXCEL` |

When `result_format` is `OutputFormat.EXCEL`, the returned bytes represent a
`.zip` archive containing the generated Excel files.

#### `parse_async(input, processing_options=None, result_format=OutputFormat.MD) → Job`

Same parameters as `parse`, minus `output`. Returns a `Job` without waiting.

#### `Job` properties

| Property | Type | Description |
|---|---|---|
| `id` | `str` | Unique job identifier |
| `processing_status` | `str` | `pending` / `processing` / `completed` / `failed` |
| `result_format` | `str` | Output format |
| `is_completed` | `bool` | True when result is ready |
| `is_failed` | `bool` | True if job failed |
| `metadata` | `DocumentMetadata` | Filename, page count, language, etc. |

---

## Notebook Integration

Results are automatically rendered when running in Jupyter:

- **`OutputFormat.MD`** → rendered Markdown
- **`OutputFormat.HTML`** → rendered HTML
- **`OutputFormat.JSON`** → interactive tree
- **`OutputFormat.TXT`** → code block

To disable auto-display, pass `output="file.md"`.

---

## Resources

- **Studio:** [studio.byteit.ai](https://studio.byteit.ai) — Process and test with a graphical user interface.
- **Colab notebook:** [Quick demo](https://colab.research.google.com/drive/1mxto7MGFVqLTbGKeSvHBSUCMvN3FZ8Uw?usp=sharing)
- **Pricing:** [byteit.ai/pricing](https://byteit.ai/pricing) — 1,000 free credits
- **Support:** [byteit.ai/support](https://byteit.ai/support)
- **LinkedIn:** [ByteIT on LinkedIn](https://www.linkedin.com/company/byteit-ai)

---

Licensed under [Apache 2.0](LICENSE). © 2026 ByteIT GmbH.
