#!/usr/bin/env python3
"""
Batch Processing Example: Process multiple documents concurrently.

This example demonstrates how to use the ByteIT library to process
multiple documents at once using async/concurrent processing.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import byteit (this is just for the local example, if you are actually using the installed library, you can skip this line)
sys.path.insert(0, str(Path(__file__).parent.parent))

from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector, S3InputConnector


def example_batch_create_jobs():
    """Example: Create multiple jobs at once (async)."""
    print("=" * 60)
    print("Example 1: Batch Job Creation (Async)")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: Please set BYTEIT_API_KEY environment variable")
        return

    # Create sample files for demonstration
    sample_files = [
        "sample_document.pdf",
        "sample_document2.pdf",
        "sample_document3.pdf",
    ]  # Add more files here

    # Filter to only existing local files
    existing_files = [f for f in sample_files if Path(f).exists()]

    if not existing_files:
        print(f"Error: No sample files found. Please ensure files exist:")
        for f in sample_files:
            print(f"  - {f}")
        return

    with ByteITClient(api_key=api_key) as client:
        # Create input connectors for each file. You can even mix connectors here:
        input_connectors = [
            LocalFileInputConnector(file_path) for file_path in existing_files
        ] + [
            S3InputConnector(
                source_bucket="tradybg-images",
                source_path_inside_bucket="1.pdf",
            )
        ]

        print(f"\nCreating {len(input_connectors)} jobs concurrently...")

        jobs = client.create_job(input_connectors, max_workers=1)

        print(f"✓ Created {len(jobs)} jobs successfully!\n")

        for i, job in enumerate(jobs):
            print(f"Job {i + 1}:")
            print(f"  ID: {job.id}")
            print(f"  Status: {job.processing_status}")
            print()


def main():
    """Run all examples."""
    print("\nByteIT Batch Processing Examples")
    print("=" * 60)

    print("\nThese examples demonstrate:")
    print("  • Creating multiple jobs concurrently")
    print("  • Processing multiple documents end-to-end")
    print("  • Async/concurrent processing with ThreadPoolExecutor")
    print()

    example_batch_create_jobs()


if __name__ == "__main__":
    main()
