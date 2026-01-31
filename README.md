# ByteIT Python SDK

ByteIT's Python library for extracting structured data from documents.
It is designed for backend services and ETL pipelines that require reliable, consistent document parsing at scale through a simple API.

---

## Installation

Install from PyPI:

```bash
pip install byteit
```

Python 3.8 or newer is required.

---

## Quick Start

```python
from byteit import ByteITClient

client = ByteITClient(api_key="your_api_key")

result = client.parse("document.pdf")
print(result.decode())
```

The returned value is raw bytes containing the parsed document content.

---

## Supported Input File Types

ByteIT supports the following file types as input:

* PDF (`.pdf`)
* Word (`.docx`)
* PowerPoint (`.pptx`)
* HTML (`.html`)
* Markdown (`.md`)
* Plain text (`.txt`)
* JSON (`.json`)
* XML (`.xml`)

---

## Basic Usage

### Parse a Local File

```python
result = client.parse("invoice.pdf")
```

By default, the output format is **Markdown (`md`)**.

---

## Output Formats

You can choose the output format depending on your pipeline needs:

```python
txt = client.parse("doc.pdf", output_format="txt")
json = client.parse("doc.pdf", output_format="json")
md = client.parse("doc.pdf", output_format="md")
html = client.parse("doc.pdf", output_format="html")
```

Supported output formats:

* Plain text (`txt`)
* JSON (`json`)
* Markdown (`md`) *(default)*
* HTML (`html`)

---

## Save Output to File

```python
client.parse(
    "doc.pdf",
    output_format="md",
    output="result.md"
)
```

When `output` is provided, the parsed result is written directly to disk.

---

## Notebook Integration

When used in Jupyter notebooks, ByteIT automatically displays results in a readable format:

* **JSON**: Interactive, expandable/collapsible tree view
* **Markdown**: Rendered with formatting (headers, lists, etc.)
* **HTML**: Rendered as HTML
* **Text**: Code block with syntax highlighting

```python
# In a Jupyter notebook - automatically displays formatted result
result = client.parse("document.pdf", result_format="json")
```

To disable auto-display, save to a file instead:

```python
# Saves to file, no auto-display
result = client.parse("doc.pdf", result_format="json", output="output.json")
```

---

## Typical Use Cases

* Extracting structured data from documents in ETL pipelines
* Preprocessing documents before indexing or downstream processing
* Automating ingestion of invoices, contracts, or reports
* Interactive document exploration in Jupyter notebooks

---

## API Reference

### `ByteITClient`

```python
ByteITClient(api_key: str)
```

Creates a new ByteIT client.

#### Parameters

* `api_key` (`str`): Your ByteIT API key

---

### `parse(...)`

```python
parse(
    input,
    output_format: str = "md",
    output = None
)
```

Parse a document and return the extracted content.

#### Parameters

* `input` (`str | Path`): Path to a local document
* `output_format` (`str`): Output format (`txt`, `json`, `md`, `html`)
* `output` (`str | Path | None`): Optional path to save the result

#### Returns

* `bytes`: Parsed document content

---

## Error Handling

The SDK exposes specific exceptions for common error cases:

```python
from byteit.exceptions import (
    ByteITError,
    ValidationError,
    AuthenticationError,
    RateLimitError,
    ServerError,
)

try:
    result = client.parse("document.pdf")
except ValidationError as e:
    print("Invalid input:", e.message)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limit exceeded")
except ByteITError as e:
    print("ByteIT error:", e.message)
```

All exceptions inherit from `ByteITError`.

---

## Configuration

### Environment Variable

You can provide the API key via environment variable:

```bash
export BYTEIT_API_KEY="your_api_key"
```

```python
import os
from byteit import ByteITClient

client = ByteITClient(api_key=os.getenv("BYTEIT_API_KEY"))
```

---

## Requirements

* Python 3.8+
* `requests`

---

## About ByteIT

ByteIT provides document parsing and data extraction APIs designed for backend systems and automation workflows.

Website: [https://byteit.ai](https://byteit.ai)

---

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

© 2026 ByteIT GmbH

---