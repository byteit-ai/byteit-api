"""
Example script demonstrating ByteIT library usage with local file connectors.
"""

import os
import sys
from pathlib import Path

# Parent directory to path to import byteit
sys.path.insert(0, str(Path(__file__).parent.parent))

from byteit import ByteITClient
from byteit.connectors import (
    LocalFileInputConnector,
    ByteITStorageOutputConnector,
)
from byteit.exceptions import (
    ByteITError,
    ValidationError,
    JobProcessingError,
    AuthenticationError,
)


def example_basic_processing():
    """Basic example: Process a local PDF file with default settings."""
    print("=" * 60)
    print("Example 1: Basic Document Processing")
    print("=" * 60)

    # Initialize the client with your API key
    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        print("Please set it with: export BYTEIT_API_KEY='your-api-key'")
        return

    client = ByteITClient(api_key=api_key)

    try:
        # Create input connector for a local file
        input_file = "sample_document.pdf"  # Replace with your file path
        if not Path(input_file).exists():
            print(f"Error: File '{input_file}' not found")
            print("Please provide a valid file path")
            return

        input_connector = LocalFileInputConnector(file_path=input_file)

        # Create output connector (stores result in ByteIT cloud storage)
        output_connector = ByteITStorageOutputConnector()

        print(f"\nProcessing file: {input_file}")
        print("Creating job...")

        # Create a job
        job = client.create_job(
            input_connector=input_connector,
            output_connector=output_connector,
        )

        print(f"Job created with ID: {job.id}")
        print(f"Status: {job.processing_status}")

        # Wait for the job to complete
        print("\nWaiting for job to complete...")
        completed_job = client.wait_for_job(
            job_id=job.id,
            poll_interval=2,  # Check every 2 seconds
            max_wait_time=300,  # Wait up to 5 minutes
        )

        print(f"Job completed! Status: {completed_job.processing_status}")

        # Get the result
        output_file = "output_result.txt"
        result_path = client.get_job_result(
            job_id=completed_job.id, output_path=output_file
        )

        print(f"\nResult saved to: {result_path}")

        # Display first few lines of the result
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read(500)  # Read first 500 chars
            print(f"\nFirst 500 characters of result:")
            print("-" * 60)
            print(content)
            print("-" * 60)

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValidationError as e:
        print(f"Validation error: {e}")
    except JobProcessingError as e:
        print(f"Job processing error: {e}")
    except AuthenticationError as e:
        print(f"Authentication error: {e}")
    except ByteITError as e:
        print(f"ByteIT API error: {e}")
    finally:
        client.close()


def example_with_processing_options():
    """Example with custom processing options."""
    print("\n" + "=" * 60)
    print("Example 2: Processing with Custom Options")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    client = ByteITClient(api_key=api_key)

    try:
        input_file = "sample_document.pdf"  # Replace with your file path
        if not Path(input_file).exists():
            print(f"Error: File '{input_file}' not found")
            return

        input_connector = LocalFileInputConnector(file_path=input_file)

        # Define custom processing options
        processing_options = {
            "output_format": "md",  # Output in Markdown format
            "ocr_model": "tesseractocr",  # Use Tesseract OCR
            "languages": ["eng", "deu"],  # Process English and German
            "page_range": "1-5",  # Only process first 5 pages
        }

        print(f"\nProcessing file: {input_file}")
        print(f"Options: {processing_options}")

        # Use the convenience method that handles creation, waiting, and result retrieval
        result_path = client.process_document(
            input_connector=input_connector,
            processing_options=processing_options,
            output_path="output_custom.md",
            poll_interval=2,
            max_wait_time=300,
        )

        print(f"\nProcessing complete! Result saved to: {result_path}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


def example_upload_only():
    """Example: Upload a file and create a job without waiting."""
    print("\n" + "=" * 60)
    print("Example 3: Upload File Only (Create Job)")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    client = ByteITClient(api_key=api_key)

    try:
        input_file = input("Enter file path to upload: ").strip()
        if not input_file or not Path(input_file).exists():
            print(f"Error: File '{input_file}' not found")
            return

        input_connector = LocalFileInputConnector(file_path=input_file)

        # Ask if user wants to configure processing options
        print("\nDo you want to configure processing options?")
        configure_options = input("(y/n) [n]: ").strip().lower()

        processing_options = None

        if configure_options == "y":
            print("\nProcessing Options (press Enter to skip any option):")
            print("-" * 60)

            # Output format
            output_format = input(
                "Output format (txt/md/json/html) [txt]: "
            ).strip()
            if not output_format:
                output_format = "txt"

            # OCR model
            print("\nOCR Model:")
            print("  - tesseractocr (Tesseract OCR)")
            print("  - easyocr (EasyOCR)")
            ocr_model = input("OCR model [tesseractocr]: ").strip()
            if not ocr_model:
                ocr_model = "tesseractocr"

            # VLM model
            print("\nVision-Language Model:")
            print("  - smoldoc (SmolDoc)")
            vlm_model = input("VLM model (optional): ").strip()

            # Languages
            print("\nLanguages (comma-separated):")
            print(
                "  Examples: eng, deu, fra, spa, ita, por, rus, jpn, kor, chi_sim"
            )
            print("  For multiple: eng,deu,fra")
            languages_input = input("Languages [eng]: ").strip()
            if not languages_input:
                languages_input = "eng"
            languages = [lang.strip() for lang in languages_input.split(",")]

            # Page range
            print("\nPage Range (Leave blank for all):")
            print("  Examples: 1-5, 1,3,5-10")
            page_range = input("Page range (Leave blank for all): ").strip()
            if not page_range:
                page_range = ""

            # Build processing options dictionary
            processing_options = {
                "output_format": output_format,
                "ocr_model": ocr_model,
                "languages": languages,
                "page_range": page_range,
            }

            # Only add VLM model if specified
            if vlm_model:
                processing_options["vlm_model"] = vlm_model

            print("\n" + "-" * 60)
            print("Processing options configured:")
            for key, value in processing_options.items():
                print(f"  {key}: {value}")
            print("-" * 60)

        print(f"\nUploading file: {input_file}")
        print("Creating job...")

        # Create job without waiting
        job = client.create_job(
            input_connector=input_connector,
            processing_options=processing_options,
        )

        print("\n✓ Job created successfully!")
        print(f"Job ID: {job.id}")
        print(f"Status: {job.processing_status}")
        print(f"Created at: {job.created_at}")
        print(
            "\nYou can check the status later using option 6 with this Job ID."
        )

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValidationError as e:
        print(f"Validation error: {e}")
    except ByteITError as e:
        print(f"ByteIT API error: {e}")
    finally:
        client.close()


def example_download_result():
    """Example: Download result for a completed job."""
    print("\n" + "=" * 60)
    print("Example 4: Download Result Only")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    job_id = input("\nEnter job ID to download result: ").strip()
    if not job_id:
        print("Error: Job ID is required")
        return

    with ByteITClient(api_key=api_key) as client:
        try:
            # First check if job is completed
            print(f"\nChecking job status...")
            job = client.get_job(job_id=job_id)

            print(f"Job ID: {job.id}")
            print(f"Status: {job.processing_status}")

            if job.metadata:
                print(f"File: {job.metadata.original_filename}")

            if not job.is_completed:
                print(
                    f"\n⚠ Job is not completed yet (status: {job.processing_status})"
                )

                if job.is_failed:
                    print(f"Job failed: {job.processing_error}")
                    return

                wait = (
                    input("Wait for job to complete? (y/n): ").strip().lower()
                )
                if wait == "y":
                    print("\nWaiting for job to complete...")
                    job = client.wait_for_job(job_id=job_id, poll_interval=2)
                    print("✓ Job completed!")
                else:
                    print("Exiting without downloading.")
                    return

            # Ask for output filename
            default_filename = f"job_{job_id[:8]}_result.txt"
            output_path = (
                input(f"\nOutput filename [{default_filename}]: ").strip()
                or default_filename
            )

            print(f"\nDownloading result...")
            result_path = client.get_job_result(
                job_id=job_id, output_path=output_path
            )

            print(f"✓ Result saved to: {result_path}")

            # Show file size
            file_size = Path(result_path).stat().st_size
            print(f"File size: {file_size:,} bytes")

            # Ask if user wants to preview
            preview = input("\nPreview file contents? (y/n): ").strip().lower()
            if preview == "y":
                with open(result_path, "r", encoding="utf-8") as f:
                    content = f.read(500)
                    print("\nFirst 500 characters:")
                    print("-" * 60)
                    print(content)
                    if len(content) >= 500:example_download_result
                        print("...")
                    print("-" * 60)

        except ByteITError as e:
            print(f"Error: {e}")


def example_list_jobs():
    """Example showing how to list jobs."""
    print("\n" + "=" * 60)
    print("Example 5: Listing Jobs")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    with ByteITClient(api_key=api_key) as client:
        try:
            # List all jobs for the authenticated user
            job_list = client.list_jobs()

            print(f"\nTotal jobs: {job_list.count}")
            print("\nRecent jobs:")
            print("-" * 60)

            for job in job_list.jobs[:10]:  # Show first 10 jobs
                status_emoji = {
                    "completed": "✓",
                    "failed": "✗",
                    "processing": "⚙",
                    "pending": "⏳",
                }.get(job.processing_status, "?")

                print(
                    f"{status_emoji} Job {job.id}: {job.processing_status} "
                    f"(created: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')})"
                )

                if job.metadata:
                    print(f"  File: {job.metadata.original_filename}")
                    print(f"  Type: {job.metadata.document_type}")

        except Exception as e:
            print(f"Error: {e}")


def example_check_job_status():
    """Example showing how to check a specific job's status."""
    print("\n" + "=" * 60)
    print("Example 6: Checking Job Status")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: BYTEIT_API_KEY environment variable not set")
        return

    job_id = input(
        "\nEnter a job ID to check (or press Enter to skip): "
    ).strip()
    if not job_id:
        print("Skipping job status check")
        return

    with ByteITClient(api_key=api_key) as client:
        try:
            # Get specific job information
            job = client.get_job(job_id=job_id)

            print(f"\nJob ID: {job.id}")
            print(f"Status: {job.processing_status}")
            print(f"Created at: {job.created_at}")
            print(f"Updated at: {job.updated_at}")

            if job.metadata:
                print(f"\nDocument Info:")
                print(f"  Filename: {job.metadata.original_filename}")
                print(f"  Type: {job.metadata.document_type}")
                print(f"  Size: {job.metadata.file_size_bytes} bytes")
                if job.metadata.page_count:
                    print(f"  Pages: {job.metadata.page_count}")

            if job.processing_options:
                print(f"\nProcessing Options:")
                for key, value in job.processing_options.items():
                    print(f"  {key}: {value}")

            if job.is_completed:
                print("\n✓ Job is completed and ready for download!")
                download = (
                    input("Download result? (y/n): ").strip().lower() == "y"
                )
                if download:
                    output_path = f"job_{job_id}_result.txt"
                    client.get_job_result(
                        job_id=job_id, output_path=output_path
                    )
                    print(f"Result saved to: {output_path}")

            elif job.is_failed:
                print(f"\n✗ Job failed: {job.processing_error}")

            elif job.is_processing:
                print("\n⚙ Job is still processing...")

        except Exception as e:
            print(f"Error: {e}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("ByteIT Library Examples - Local File Processing")
    print("=" * 60)

    # Check if API key is set
    if not os.environ.get("BYTEIT_API_KEY"):
        print("\n⚠ WARNING: BYTEIT_API_KEY environment variable is not set")
        print("Please set it before running examples:")
        print("  export BYTEIT_API_KEY='your-api-key-here'")
        return

    print("\nWhich example would you like to run?")
    print("1. Basic document processing")
    print("2. Processing with custom options")
    print("3. Upload file only (create job)")
    print("4. Download result only")
    print("5. List all jobs")
    print("6. Check job status")
    print("0. Exit")

    choice = input("\nEnter your choice (0-6): ").strip()

    examples = {
        "1": example_basic_processing,
        "2": example_with_processing_options,
        "3": example_upload_only,
        "4": example_download_result,
        "5": example_list_jobs,
        "6": example_check_job_status,
    }

    if choice == "0":
        print("Goodbye!")
    elif choice in examples:
        examples[choice]()
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()
