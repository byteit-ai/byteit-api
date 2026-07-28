# ByteIT Python SDK

ByteIT is a Python client for document parsing and structured extraction. Submit files, retrieve parsed content, and extract schema-based data from completed jobs.

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Parse Documents](#parse-documents)
- [Structured Extraction](#structured-extraction)
- [Saved Schemas](#saved-schemas)
- [Custom Jobs](#custom-jobs)
- [Batch Processing from a Folder](#batch-processing-from-a-folder)
- [Processing Options](#processing-options)
- [Error Handling](#error-handling)
- [Supported Inputs](#supported-inputs)
- [Notebook Behavior](#notebook-behavior)
- [HTTP API Examples](#http-api-examples-curl--typescript)
- [Resources](#resources)

## Installation

```bash
pip install byteit
```

Requires Python 3.8+ and a ByteIT API key. For structured extraction, install with `pip install byteit`.

## Quick Start

```python
from byteit import ByteITClient

client = ByteITClient(api_key="your_api_key")
result = client.parse("document.pdf")
print(result.decode("utf-8"))
```

`parse()` returns raw bytes. Pass `output="result.json"` to write directly to disk.

## Parse Documents

```python
from byteit import ByteITClient, ProcessingOptions

client = ByteITClient(api_key="your_api_key")

# Synchronous — blocks until complete
result = client.parse(
    "invoice.pdf",
    processing_options=ProcessingOptions(languages=["en"], page_range="1-2"),
)

# Asynchronous — returns immediately, poll manually
job = client.parse_async("document.pdf")
status = client.get_job_status(job.id)
if status.is_completed:
    result = client.get_parse_job_result(job.id)
```

Available parse-job methods:

| Method | Purpose |
|---|---|
| `get_parse_jobs()` | List parse jobs |
| `get_parse_job_details(job_id)` | Get full parse-job details |
| `get_job_status(job_id)` | Check lightweight processing status |
| `get_parse_job_result(job_id, result_format=None)` | Download parse result |

## Structured Extraction

Extraction runs on a completed parse job and returns a dictionary matching your schema. Schemas support nesting, lists, and mixed data types.

### Example: Invoice (flat fields)

```python
from byteit import ByteITClient, ExtractionSchema
from pydantic import Field


class InvoiceSchema(ExtractionSchema):
    invoice_number: str | None = Field(description="The invoice number or reference")
    total_amount: str | None = Field(description="Total amount due including tax")
    due_date: str | None = Field(description="Payment due date")
    vendor_name: str | None = Field(description="Name of the vendor or supplier")


client = ByteITClient(api_key="your_api_key")
parse_job = client.parse_async("invoice.pdf")

result = client.extract(parse_job.id, InvoiceSchema, extraction_complexity="medium")
```

### Example: Logistics (nested model with lists)

```python
from pydantic import Field
from byteit import ExtractionSchema


class Consignee(ExtractionSchema):
    name: str | None = Field(description="Recipient/consignee name")
    address: str | None = Field(description="Delivery address")
    city: str | None = Field(description="City of delivery")
    country: str | None = Field(description="Country code or name")


class ShipmentItem(ExtractionSchema):
    description: str | None = Field(description="Item description or HS code")
    quantity: str | None = Field(description="Number of units or packages")
    weight_kg: str | None = Field(description="Weight in kilograms")


class LogisticsSchema(ExtractionSchema):
    bill_of_lading_number: str | None = Field(description="Bill of lading or waybill number")
    vessel_or_flight: str | None = Field(description="Vessel name or flight number")
    port_of_loading: str | None = Field(description="Port or airport of origin")
    port_of_discharge: str | None = Field(description="Port or airport of destination")
    consignee: Consignee | None = Field(description="Consignee information")
    items: list[ShipmentItem] | None = Field(description="Cargo line items")


logistics_result = client.extract(parse_job.id, LogisticsSchema)
```

### Example: Medical Report (mixed types, nested arrays)

```python
from pydantic import Field
from byteit import ExtractionSchema
from datetime import date


class Medication(ExtractionSchema):
    name: str | None = Field(description="Medication name")
    dosage: str | None = Field(description="Dosage and frequency")
    duration: str | None = Field(description="Prescribed duration")


class LabResult(ExtractionSchema):
    test_name: str | None = Field(description="Laboratory test name")
    value: str | None = Field(description="Measured value with unit")
    reference_range: str | None = Field(description="Normal reference range")


class MedicalReportSchema(ExtractionSchema):
    patient_name: str | None = Field(description="Full name of patient")
    date_of_birth: str | None = Field(description="Patient date of birth")
    report_date: str | None = Field(description="Date of the medical report")
    diagnosis: str | None = Field(description="Primary diagnosis or impression")
    medications: list[Medication] | None = Field(description="Prescribed medications")
    lab_results: list[LabResult] | None = Field(description="Laboratory results")
    notes: str | None = Field(description="Additional physician notes or comments")


medical_result = client.extract(parse_job.id, MedicalReportSchema)
```

Async extraction is also available:

```python
extract_job = client.extract_async(parse_job.id, MedicalReportSchema)
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

## Saved Schemas

Save extraction schemas by name and reuse them across jobs without redefining them in code.

```python
# Save
client.save_schema("invoice", InvoiceSchema)

# List all saved schemas
saved_schemas = client.get_saved_schemas()
for s in saved_schemas.schemas:
    print(s.name)

# Retrieve and use
saved = client.get_saved_schema("invoice")
result = client.extract(parse_job.id, saved)

# Delete
client.delete_saved_schema("invoice")
```

Available saved-schema methods:

| Method | Purpose |
|---|---|
| `save_schema(name, schema)` | Persist a reusable extraction schema |
| `get_saved_schemas()` | List all saved schemas for your account |
| `get_saved_schema(name)` | Retrieve one saved schema by name |
| `delete_saved_schema(name)` | Delete a saved schema by name |

## Custom Jobs

Custom jobs are a **private, plan-specific feature** — they require prior authorization and a dedicated connection to ByteIT. They allow submitting one or more documents with an optional schema and user prompt, processed by a model configured for your plan.

```python
# Synchronous — waits for result
result = client.custom_job(
    ["agreement.pdf"],
    schema=InvoiceSchema,
    user_prompt="Extract all financial figures and party names.",
    nickname="Q4 agreements",
)

# Asynchronous — submit and poll later
job = client.custom_job_async(
    "document.pdf",
    schema=InvoiceSchema,
    user_prompt="Focus on the liability clauses.",
)
status = client.get_job_status(job.id)
if status.is_completed:
    result = client.get_custom_job_result(job.id)
```

Available custom-job methods:

| Method | Purpose |
|---|---|
| `custom_job(input, schema=None, user_prompt=None, nickname=None)` | Submit documents for a custom job and wait |
| `custom_job_async(input, schema=None, user_prompt=None, nickname=None)` | Submit a custom job and return immediately |
| `get_custom_jobs(before=None)` | List custom jobs for your account |
| `get_custom_job_result(job_id)` | Download the result of a completed custom job |

## Batch Processing from a Folder

Submit all supported files in a folder at once. The SDK packs files into batched requests respecting per-request limits, handles rate limiting with automatic retries and adaptive spacing.

```python
from byteit import ByteITClient

client = ByteITClient(api_key="your_api_key")

# All supported files in the folder (recursively) are submitted as batch jobs
jobs = client.parse_async("./invoices_folder")
for job in jobs:
    print(job.id, job.processing_status)

# Or explicitly list files
jobs = client.parse_async(["./invoice1.pdf", "./invoice2.pdf"])
```

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

Supported fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `languages` | `list[str]` | `["en"]` | Language codes for OCR/parsing |
| `page_range` | `str` | `""` (all pages) | Pages to process, e.g. `"1-5"` or `"1,3,5"` |
| `extraction_type` | `str` | `"auto"` | One of `"auto"`, `"complex"`, `"ocr"`, etc. |
| `image_annotations` | `bool` | `False` | Enable image annotation extraction |
| `force_image_annotations` | `bool` | `False` | Force annotation extraction even when the image is detected as useless |
| `table_enrichment` | `bool` | `False` | Enable table enrichment |

## Error Handling

All SDK exceptions inherit from `ByteITError`.

| Exception | HTTP Status | Meaning |
|---|---|---|
| `AuthenticationError` | 401 | Invalid API key |
| `APIKeyError` | 403 | API key not authorised |
| `ValidationError` | 400 | Invalid request parameters |
| `RateLimitError` | 429 | Too many requests |
| `ResourceNotFoundError` | 404 | Job or resource not found |
| `ServerError` | 500+ | ByteIT server error |
| `JobProcessingError` | — | Job failed during processing |

```python
from byteit.exceptions import ByteITError, AuthenticationError, ValidationError

try:
    result = client.parse("document.pdf")
except AuthenticationError:
    print("Invalid API key")
except ValidationError as exc:
    print("Invalid request:", exc.message)
except ByteITError as exc:
    print("ByteIT error:", exc.message)
```

## Supported Inputs

PDF, Word (`.docx`), PowerPoint (`.pptx`), HTML, Markdown, plain text, JSON, XML, and common image formats (PNG, JPEG, TIFF, BMP).

## Notebook Behavior

When running in Jupyter, parse results are automatically displayed as JSON when possible. Pass `output=...` to suppress inline display and save the response directly.

## HTTP API Examples (cURL + TypeScript)

For direct HTTP usage without the SDK, including tested request snippets for every endpoint, see [docs/api-curl-typescript-examples.md](docs/api-curl-typescript-examples.md).

## Resources

- Studio: [studio.byteit.ai](https://studio.byteit.ai)
- Pricing: [byteit.ai/pricing](https://byteit.ai/pricing)
- Support: [byteit.ai/support](https://byteit.ai/support)
- LinkedIn: [ByteIT on LinkedIn](https://www.linkedin.com/company/byteit-ai)

Licensed under [Apache 2.0](LICENSE). © 2026 ByteIT GmbH.
