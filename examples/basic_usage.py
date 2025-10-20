"""Basic usage examples for the ByteIT client library."""

from byteit import ByteITClient

# Replace with your actual API key
API_KEY = "your-api-key-here"


def example_basic_processing():
    """Example: Basic document processing."""
    print("Example 1: Basic Processing")
    print("-" * 50)

    client = ByteITClient(api_key=API_KEY)

    # Process a document
    result = client.process_document(
        "sample.pdf", file_type="pdf", output_path="output.md"
    )

    print(f"Document processed and saved to: {result}")
    print()


def example_step_by_step():
    """Example: Step-by-step processing with status checks."""
    print("Example 2: Step-by-Step Processing")
    print("-" * 50)

    client = ByteITClient(api_key=API_KEY)

    # Step 1: Create job
    with open("sample.pdf", "rb") as f:
        job = client.create_job(f, file_type="pdf")
    print(f"Job created: {job.id}")
    print(f"Initial status: {job.processing_status}")

    # Step 2: Wait for completion
    print("Waiting for job to complete...")
    completed_job = client.wait_for_job(job.id, poll_interval=2)
    print(f"Job completed: {completed_job.processing_status}")

    # Step 3: Download result
    result = client.get_job_result(job.id, output_path="output.md")
    print(f"Result saved to: {result}")
    print()


def example_list_jobs():
    """Example: List all jobs."""
    print("Example 3: List All Jobs")
    print("-" * 50)

    client = ByteITClient(api_key=API_KEY)

    job_list = client.list_jobs()
    print(f"Total jobs: {job_list.count}")

    for job in job_list.jobs[:5]:  # Show first 5
        print(f"  - Job {job.id}")
        print(f"    Status: {job.processing_status}")
        print(f"    Created: {job.created_at}")
    print()


def example_with_context_manager():
    """Example: Using context manager."""
    print("Example 4: Context Manager")
    print("-" * 50)

    with ByteITClient(api_key=API_KEY) as client:
        result = client.process_document(
            "sample.pdf", file_type="pdf", output_path="output.md"
        )
        print(f"Processed: {result}")

    print("Client automatically closed")
    print()


def example_error_handling():
    """Example: Error handling."""
    print("Example 5: Error Handling")
    print("-" * 50)

    from byteit import APIKeyError, JobProcessingError, ResourceNotFoundError

    try:
        client = ByteITClient(api_key=API_KEY)

        # Try to get a non-existent job
        job = client.get_job("non-existent-job-id")

    except APIKeyError as e:
        print(f"API Key Error: {e.message}")
    except ResourceNotFoundError as e:
        print(f"Resource Not Found: {e.message}")
    except JobProcessingError as e:
        print(f"Processing Error: {e.message}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    print()


def example_custom_options():
    """Example: Custom processing options."""
    print("Example 6: Custom Processing Options")
    print("-" * 50)

    client = ByteITClient(api_key=API_KEY)

    # Define custom processing options
    processing_options = {
        "ocr_enabled": True,
        "language": "en",
        "extract_tables": True,
        "extract_images": False,
    }

    result = client.process_document(
        "sample.pdf",
        file_type="pdf",
        output_format="markdown",
        processing_options=processing_options,
        output_path="output_custom.md",
    )

    print(f"Document processed with custom options: {result}")
    print()


def example_multiple_files():
    """Example: Process multiple files."""
    print("Example 7: Process Multiple Files")
    print("-" * 50)

    client = ByteITClient(api_key=API_KEY)

    files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    jobs = []

    # Create jobs for all files
    for file_path in files:
        try:
            job = client.create_job(file_path, file_type="pdf")
            jobs.append((file_path, job))
            print(f"Created job for {file_path}: {job.id}")
        except Exception as e:
            print(f"Failed to create job for {file_path}: {e}")

    # Wait for all jobs to complete
    for file_path, job in jobs:
        try:
            completed_job = client.wait_for_job(job.id)
            output_path = f"output_{file_path.replace('.pdf', '.md')}"
            result = client.get_job_result(job.id, output_path=output_path)
            print(f"Completed {file_path} -> {result}")
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")

    print()


if __name__ == "__main__":
    # Run examples
    # Uncomment the examples you want to run

    # example_basic_processing()
    # example_step_by_step()
    # example_list_jobs()
    # example_with_context_manager()
    # example_error_handling()
    # example_custom_options()
    # example_multiple_files()

    print("Examples completed!")
    print("\nNote: Replace 'your-api-key-here' with your actual API key")
    print("and ensure you have sample files to test with.")
