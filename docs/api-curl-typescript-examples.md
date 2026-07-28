# ByteIT HTTP API Examples (cURL + TypeScript)

This guide shows direct HTTP requests for all ByteIT job endpoints used by this SDK.

Base URL used in all examples:

```text
https://byteit.ai/v1/jobs
```

## Prerequisites

- A valid API key in `.env` as `BYTEIT_API_KEY=...`
- `example.pdf` in the repository root
- Node.js 18+ for TypeScript examples

## Common Setup

### cURL setup

```bash
export BYTEIT_API_KEY="<your_api_key>"
```

PowerShell:

```powershell
$env:BYTEIT_API_KEY = "<your_api_key>"
```

### TypeScript setup

```ts
const BASE_URL = "https://byteit.ai/v1/jobs";
const API_KEY = process.env.BYTEIT_API_KEY!;
const HEADERS = {
  "X-API-Key": API_KEY,
};
```

## 1) Create Parse Job

`POST /parse-jobs/`

### cURL

```bash
curl -X POST "https://byteit.ai/v1/jobs/parse-jobs/" \
  -H "X-API-Key: $BYTEIT_API_KEY" \
  -F "file=@example.pdf" \
  -F "output_format=json" \
  -F "processing_options={}" \
  -F "input_connector=localfile" \
  -F "output_connector=localfile" \
  -F "output_connection_data={}"
```

### TypeScript

```ts
import { openAsBlob } from "node:fs";

const fileBlob = await openAsBlob("example.pdf");
const form = new FormData();
form.append("file", fileBlob, "example.pdf");
form.append("output_format", "json");
form.append("processing_options", "{}");
form.append("input_connector", "localfile");
form.append("output_connector", "localfile");
form.append("output_connection_data", "{}");

const createParseRes = await fetch(`${BASE_URL}/parse-jobs/`, {
  method: "POST",
  headers: HEADERS,
  body: form,
});
const createParseJson = await createParseRes.json();
const parseJobId = createParseJson.parse_job.id;
```

## 2) List Parse Jobs

`GET /parse-jobs/`

### cURL

```bash
curl -X GET "https://byteit.ai/v1/jobs/parse-jobs/" \
  -H "X-API-Key: $BYTEIT_API_KEY"
```

### TypeScript

```ts
const parseJobsRes = await fetch(`${BASE_URL}/parse-jobs/`, {
  method: "GET",
  headers: HEADERS,
});
const parseJobsJson = await parseJobsRes.json();
```

## 3) Parse Job Details

`GET /parse-jobs/{job_id}/`

### cURL

```bash
curl -X GET "https://byteit.ai/v1/jobs/parse-jobs/${PARSE_JOB_ID}/" \
  -H "X-API-Key: $BYTEIT_API_KEY"
```

### TypeScript

```ts
const parseDetailsRes = await fetch(`${BASE_URL}/parse-jobs/${parseJobId}/`, {
  method: "GET",
  headers: HEADERS,
});
const parseDetailsJson = await parseDetailsRes.json();
```

## 4) Generic Job Status

`GET /{job_id}/status/`

### cURL

```bash
curl -X GET "https://byteit.ai/v1/jobs/${PARSE_JOB_ID}/status/" \
  -H "X-API-Key: $BYTEIT_API_KEY"
```

### TypeScript

```ts
const parseStatusRes = await fetch(`${BASE_URL}/${parseJobId}/status/`, {
  method: "GET",
  headers: HEADERS,
});
const parseStatusJson = await parseStatusRes.json();
```

## 5) Parse Job Result (default format)

`GET /parse-jobs/{job_id}/result/`

### cURL

```bash
curl -X GET "https://byteit.ai/v1/jobs/parse-jobs/${PARSE_JOB_ID}/result/" \
  -H "X-API-Key: $BYTEIT_API_KEY" \
  --output parse-result.bin
```

### TypeScript

```ts
const parseResultRes = await fetch(`${BASE_URL}/parse-jobs/${parseJobId}/result/`, {
  method: "GET",
  headers: HEADERS,
});
const parseResultBuffer = Buffer.from(await parseResultRes.arrayBuffer());
```

## 6) Parse Job Result (TXT override)

`GET /parse-jobs/{job_id}/result/?output_format=txt`

### cURL

```bash
curl -X GET "https://byteit.ai/v1/jobs/parse-jobs/${PARSE_JOB_ID}/result/?output_format=txt" \
  -H "X-API-Key: $BYTEIT_API_KEY" \
  --output parse-result.txt
```

### TypeScript

```ts
const parseTxtRes = await fetch(
  `${BASE_URL}/parse-jobs/${parseJobId}/result/?output_format=txt`,
  {
    method: "GET",
    headers: HEADERS,
  },
);
const parseTxt = await parseTxtRes.text();
```

## 7) Create Extract Job

`POST /extract-jobs/`

### cURL

```bash
cat > extract-payload.json <<'JSON'
{
  "parse_job_id": "<completed_parse_job_id>",
  "schema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "Document title"
      }
    },
    "required": []
  },
  "extraction_complexity": "medium"
}
JSON

curl -X POST "https://byteit.ai/v1/jobs/extract-jobs/" \
  -H "X-API-Key: $BYTEIT_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @extract-payload.json
```

### TypeScript

```ts
const createExtractRes = await fetch(`${BASE_URL}/extract-jobs/`, {
  method: "POST",
  headers: {
    ...HEADERS,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    parse_job_id: parseJobId,
    schema: {
      type: "object",
      properties: {
        title: {
          type: "string",
          description: "Document title",
        },
      },
      required: [],
    },
    extraction_complexity: "medium",
  }),
});
const createExtractJson = await createExtractRes.json();
const extractJobId = createExtractJson.extract_job.id;
```

## 8) List Extract Jobs

`GET /extract-jobs/`

### cURL

```bash
curl -X GET "https://byteit.ai/v1/jobs/extract-jobs/" \
  -H "X-API-Key: $BYTEIT_API_KEY"
```

### TypeScript

```ts
const extractJobsRes = await fetch(`${BASE_URL}/extract-jobs/`, {
  method: "GET",
  headers: HEADERS,
});
const extractJobsJson = await extractJobsRes.json();
```

## 9) Extract Job Details

`GET /extract-jobs/{job_id}/`

### cURL

```bash
curl -X GET "https://byteit.ai/v1/jobs/extract-jobs/${EXTRACT_JOB_ID}/" \
  -H "X-API-Key: $BYTEIT_API_KEY"
```

### TypeScript

```ts
const extractDetailsRes = await fetch(`${BASE_URL}/extract-jobs/${extractJobId}/`, {
  method: "GET",
  headers: HEADERS,
});
const extractDetailsJson = await extractDetailsRes.json();
```

## 10) Extract Job Result

`GET /extract-jobs/{job_id}/result/`

### cURL

```bash
curl -X GET "https://byteit.ai/v1/jobs/extract-jobs/${EXTRACT_JOB_ID}/result/" \
  -H "X-API-Key: $BYTEIT_API_KEY"
```

### TypeScript

```ts
const extractResultRes = await fetch(`${BASE_URL}/extract-jobs/${extractJobId}/result/`, {
  method: "GET",
  headers: HEADERS,
});
const extractResultJson = await extractResultRes.json();
```

## Validation Status

All endpoint examples in this file were executed successfully against the live API on 2026-05-12 with:

- `example.pdf` from this repository
- cURL requests (HTTP 200 for all listed endpoints)
- TypeScript requests (end-to-end run completed successfully)
