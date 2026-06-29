#!/usr/bin/env python3
"""Temporary script to exercise async batch parse + rate-limit handling.

Usage:
    export BYTEIT_API_KEY="your_api_key"
    PYTHONPATH=. python rate_limit_test/run_batch_async_test.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from byteit import ByteITClient
from byteit.exceptions import ByteITError, RateLimitError

SCRIPT_DIR = Path(__file__).resolve().parent
SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md", ".html"}


def collect_files(folder: Path) -> list[Path]:
    """Return supported document files from a folder, sorted by name."""
    files = [
        path
        for path in sorted(folder.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"No supported files found in {folder}")
    return files


def main() -> int:
    """Submit all files in this folder for async batch parsing."""
    api_key = os.getenv("BYTEIT_API_KEY")
    if not api_key:
        print("BYTEIT_API_KEY is not set.", file=sys.stderr)
        return 1

    files = collect_files(SCRIPT_DIR)
    client = ByteITClient(api_key)

    submitted: list[tuple[str, str]] = []
    failed: list[tuple[str, str]] = []

    print(f"Submitting {len(files)} files from {SCRIPT_DIR} with queue_for_batch=True\n")

    started_at = time.monotonic()
    for index, file_path in enumerate(files, start=1):
        print(f"[{index}/{len(files)}] {file_path.name}")
        try:
            job = client.parse_async(file_path, queue_for_batch=True)
            submitted.append((file_path.name, job.id))
            print(f"  -> job_id={job.id}")
        except RateLimitError as exc:
            failed.append((file_path.name, str(exc.message)))
            print(f"  -> FAILED after retries: {exc.message}", file=sys.stderr)
        except ByteITError as exc:
            failed.append((file_path.name, str(exc.message)))
            print(f"  -> FAILED: {exc.message}", file=sys.stderr)

    elapsed = time.monotonic() - started_at
    print("\n=== Summary ===")
    print(f"Submitted: {len(submitted)}")
    print(f"Failed:    {len(failed)}")
    print(f"Elapsed:   {elapsed:.1f}s")

    if submitted:
        print("\nSubmitted files:")
        for name, job_id in submitted:
            print(f"  {name} -> {job_id}")

    if failed:
        print("\nFailed files:")
        for name, error in failed:
            print(f"  {name} -> {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
