"""
Example demonstrating S3 integration with ByteIT.

This example shows how to:
1. Process files directly from S3 (no local download)
2. Save results directly to S3 (no local upload)
3. Process multiple S3 files in batch

Prerequisites:
    - ByteIT API key
    - AWS IAM role configured in ByteIT dashboard
    - S3 buckets with appropriate permissions
"""

import os
import sys
from pathlib import Path

# Parent directory to path to import byteit
sys.path.insert(0, str(Path(__file__).parent.parent))

from byteit import ByteITClient
from byteit.connectors import S3InputConnector, S3OutputConnector
from byteit.exceptions import ByteITError


def example_s3_to_local():
    """
    Example 1: Fetch file from S3, process, and save result locally.

    The file is fetched by ByteIT server (not downloaded to your machine),
    processed, and the result is downloaded to your local machine.
    """
    print("=" * 60)
    print("Example 1: S3 Input -> Local Output")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    client = ByteITClient(api_key=api_key)

    try:
        # Input from S3
        input_connector = S3InputConnector(
            source_bucket="my-documents-bucket",
            source_path_inside_bucket="invoices/invoice-001.pdf",
        )

        print("\nProcessing file from S3...")
        print(f"Bucket: {input_connector.source_bucket}")
        print(f"Path: {input_connector.source_path_inside_bucket}")

        # Process and save locally
        result_path = client.process_document(
            input_connector=input_connector,
            processing_options={"output_format": "txt"},
            output_path="invoice_result.txt",
            poll_interval=5,
            max_wait_time=600,
        )

        print(f"\n✓ Result saved to: {result_path}")

        # Display first few lines
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read(500)
            print("\nFirst 500 characters:")
            print("-" * 60)
            print(content)
            print("-" * 60)

    except ByteITError as e:
        print(f"\nError: {e}")
    finally:
        client.close()


def example_s3_to_s3():
    """
    Example 2: Process file from S3 and save result to S3.

    True server-to-server processing. The file never passes through
    your local machine. ByteIT server fetches from source S3,
    processes, and saves to destination S3.
    """
    print("\n" + "=" * 60)
    print("Example 2: S3 Input -> S3 Output (Server-to-Server)")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    client = ByteITClient(api_key=api_key)

    try:
        # Input from S3
        input_connector = S3InputConnector(
            source_bucket="tradybg-images",
            source_path_inside_bucket="1.pdf",
        )

        # Output to S3
        output_connector = S3OutputConnector(
            bucket="tradybg-images",
            path="output/",
        )

        print("\nProcessing S3 to S3...")
        print(
            f"Source: s3://{input_connector.source_bucket}/{input_connector.source_path_inside_bucket}"
        )
        print(
            f"Destination: s3://{output_connector.bucket}/{output_connector.path}"
        )

        # Create job
        job = client.create_job(
            nickname="Library S3 to S3 Example",
            input_connector=input_connector,
            output_connector=output_connector,
            processing_options={"output_format": "md", "languages": ["en"]},
        )

        print(f"\n✓ Job created: {job.id}")
        print(f"Status: {job.processing_status}")

        # Wait for completion
        print("\nWaiting for processing to complete...")
        completed_job = client.wait_for_job(
            job_id=job.id, poll_interval=5, max_wait_time=600
        )

        print(f"\n✓ Job completed!")
        print(
            f"Result saved to S3: s3://{output_connector.bucket}/{output_connector.path}"
        )

    except ByteITError as e:
        print(f"\nError: {e}")
    finally:
        client.close()


def example_batch_s3_processing():
    """
    Example 3: Process multiple files from S3 in batch.

    All files are processed concurrently on the ByteIT server.
    Results can be saved to S3 or downloaded locally.
    """
    print("\n" + "=" * 60)
    print("Example 3: Batch S3 Processing")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    client = ByteITClient(api_key=api_key)

    try:
        # List of S3 files to process
        s3_files = [
            "invoices/2024/Q1/invoice-001.pdf",
            "invoices/2024/Q1/invoice-002.pdf",
            "invoices/2024/Q1/invoice-003.pdf",
            "invoices/2024/Q1/invoice-004.pdf",
            "invoices/2024/Q1/invoice-005.pdf",
        ]

        # Create input connectors
        input_connectors = [
            S3InputConnector(
                source_bucket="company-documents",
                source_path_inside_bucket=path,
            )
            for path in s3_files
        ]

        # Output connector (all results go here)
        output_connector = S3OutputConnector(
            bucket="company-processed", path="invoices/2024/Q1/processed/"
        )

        print(f"\nProcessing {len(input_connectors)} files from S3...")
        print(f"Source bucket: company-documents")
        print(
            f"Destination: s3://company-processed/invoices/2024/Q1/processed/"
        )

        # Create all jobs
        jobs = client.create_job(
            input_connector=input_connectors,
            output_connector=output_connector,
            processing_options={
                "output_format": "json",
                "languages": ["eng"],
                "ocr_model": "tesseractocr",
            },
            max_workers=5,  # Process up to 5 concurrently
        )

        print(f"\n✓ Created {len(jobs)} jobs")

        # Wait for all jobs to complete
        for i, job in enumerate(jobs, 1):
            print(f"\nWaiting for job {i}/{len(jobs)} ({job.id})...")
            completed = client.wait_for_job(
                job_id=job.id, poll_interval=5, max_wait_time=600
            )
            print(f"✓ Job {i} completed")

        print(f"\n✓ All {len(jobs)} jobs completed successfully!")
        print(
            f"Results available in: s3://company-processed/invoices/2024/Q1/processed/"
        )

    except ByteITError as e:
        print(f"\nError: {e}")
    finally:
        client.close()


def example_mixed_local_s3():
    """
    Example 4: Mixed local and S3 usage.

    Process a local file and save result to S3.
    """
    print("\n" + "=" * 60)
    print("Example 4: Local Input -> S3 Output")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    from byteit.connectors import LocalFileInputConnector

    client = ByteITClient(api_key=api_key)

    try:
        # Input from local file
        local_file = "sample_document.pdf"
        if not Path(local_file).exists():
            print(f"Error: {local_file} not found")
            return

        input_connector = LocalFileInputConnector(local_file)

        # Output to S3
        output_connector = S3OutputConnector(
            bucket="my-results", path="uploads/processed/"
        )

        print(f"\nProcessing local file: {local_file}")
        print(f"Will save to: s3://my-results/uploads/processed/")

        job = client.create_job(
            input_connector=input_connector,
            output_connector=output_connector,
            processing_options={"output_format": "txt"},
        )

        print(f"\n✓ Job created: {job.id}")

        completed = client.wait_for_job(job.id, poll_interval=5)
        print(f"✓ Processing complete! Result saved to S3")

    except ByteITError as e:
        print(f"\nError: {e}")
    finally:
        client.close()


def example_check_job_with_s3_output():
    """
    Example 5: Check job status and handle S3 output.
    """
    print("\n" + "=" * 60)
    print("Example 5: Check Job with S3 Output")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    job_id = input("\nEnter job ID to check: ").strip()
    if not job_id:
        print("No job ID provided")
        return

    client = ByteITClient(api_key=api_key)

    try:
        # Get job details
        job = client.get_job(job_id=job_id)

        print(f"\nJob ID: {job.id}")
        print(f"Status: {job.processing_status}")
        print(f"Created: {job.created_at}")

        if job.metadata:
            print(f"\nDocument Info:")
            print(f"  Filename: {job.metadata.original_filename}")
            print(f"  Type: {job.metadata.document_type}")
            print(f"  Size: {job.metadata.file_size_bytes} bytes")

        # Check output connector
        if hasattr(job, "output_connector") and job.output_connector == "s3":
            print(f"\nOutput Configuration: S3")
            if hasattr(job, "output_connection_data"):
                output_data = job.output_connection_data
                print(f"  Bucket: {output_data.get('bucket', 'N/A')}")
                print(f"  Path: {output_data.get('path', 'N/A')}")

        if job.is_completed:
            print("\n✓ Job completed successfully!")
            print("Result is available in the configured S3 bucket.")
        elif job.is_failed:
            print(f"\n✗ Job failed: {job.processing_error}")
        elif job.is_processing:
            print("\n⚙ Job is still processing...")

    except ByteITError as e:
        print(f"\nError: {e}")
    finally:
        client.close()


def main():
    """Run S3 integration examples."""
    print("\n" + "=" * 60)
    print("ByteIT S3 Integration Examples")
    print("=" * 60)

    if not os.environ.get("BYTEIT_API_KEY"):
        print("\n⚠ WARNING: BYTEIT_API_KEY environment variable not set")
        print("Please set it before running examples:")
        print("  export BYTEIT_API_KEY='your-api-key-here'")
        return

    print("\n📌 Prerequisites:")
    print("  - AWS IAM role configured in ByteIT dashboard")
    print("  - S3 buckets with appropriate permissions")
    print("  - External ID configured (if required)")

    print("\nWhich example would you like to run?")
    print("1. S3 to Local (download result)")
    print("2. S3 to S3 (server-to-server)")
    print("3. Batch S3 processing")
    print("4. Local to S3 (upload result)")
    print("5. Check job with S3 output")
    print("0. Exit")

    choice = input("\nEnter your choice (0-5): ").strip()

    examples = {
        "1": example_s3_to_local,
        "2": example_s3_to_s3,
        "3": example_batch_s3_processing,
        "4": example_mixed_local_s3,
        "5": example_check_job_with_s3_output,
    }

    if choice == "0":
        print("Goodbye!")
    elif choice in examples:
        examples[choice]()
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()
