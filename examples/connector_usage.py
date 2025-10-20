"""Example usage of ByteIT client with connectors."""

from byteit import (
    ByteITClient,
    LocalFileInputConnector,
    ByteITStorageOutputConnector,
)

# Replace with your actual API key
API_KEY = "your-api-key-here"


def example_with_connectors():
    """Example: Using input and output connectors."""
    print("Example: Using Connectors")
    print("-" * 50)

    client = ByteITClient(api_key=API_KEY)

    # Create input connector for local file
    input_connector = LocalFileInputConnector("sample.pdf")

    # Create output connector (results saved on ByteIT cloud)
    output_connector = ByteITStorageOutputConnector()

    # Define processing options
    processing_options = {
        "ocr_model": "tesseract",
        "vlm_model": "gpt-4-vision",
        "languages": ["en", "de"],
        "page_range": "1-10",
        "output_format": "markdown",
    }

    # Create job
    job = client.create_job(
        input_connector=input_connector,
        output_connector=output_connector,
        processing_options=processing_options,
    )

    print(f"Job created: {job.id}")
    print(f"Status: {job.processing_status}")

    # Wait for job to complete
    completed_job = client.wait_for_job(job.id)
    print(f"Job completed: {completed_job.processing_status}")

    # Download result
    result = client.get_job_result(job.id, output_path="output.md")
    print(f"Result saved to: {result}")
    print()


def example_simple_processing():
    """Example: Simple one-step processing."""
    print("Example: Simple Processing")
    print("-" * 50)

    client = ByteITClient(api_key=API_KEY)

    # Create connectors
    input_connector = LocalFileInputConnector("sample.pdf")
    output_connector = ByteITStorageOutputConnector()

    # Process in one call
    result = client.process_document(
        input_connector=input_connector,
        output_connector=output_connector,
        processing_options={
            "languages": ["en"],
            "output_format": "json",
        },
        output_path="output.json",
    )

    print(f"Document processed and saved to: {result}")
    print()


def example_minimal():
    """Example: Minimal usage with defaults."""
    print("Example: Minimal Usage")
    print("-" * 50)

    client = ByteITClient(api_key=API_KEY)

    # Minimal usage - output connector defaults to ByteITStorageOutputConnector
    input_connector = LocalFileInputConnector("sample.pdf")

    job = client.create_job(input_connector=input_connector)

    print(f"Job created with defaults: {job.id}")
    print()


def example_validation():
    """Example: Processing options validation."""
    print("Example: Validation")
    print("-" * 50)

    from byteit import ValidationError

    client = ByteITClient(api_key=API_KEY)
    input_connector = LocalFileInputConnector("sample.pdf")

    # This will raise ValidationError due to unexpected field
    try:
        processing_options = {
            "ocr_model": "tesseract",
            "invalid_field": "some_value",  # This field is not expected
        }

        job = client.create_job(
            input_connector=input_connector,
            processing_options=processing_options,
        )
    except ValidationError as e:
        print(f"Validation error caught: {e.message}")

    # Valid processing options
    processing_options = {
        "ocr_model": "tesseract",
        "vlm_model": "claude-vision",
        "languages": ["en", "fr"],
        "page_range": "all",
        "output_format": "html",
    }

    job = client.create_job(
        input_connector=input_connector,
        processing_options=processing_options,
    )
    print(f"Valid job created: {job.id}")
    print()


if __name__ == "__main__":
    # Run examples
    # Uncomment the examples you want to run

    # example_with_connectors()
    # example_simple_processing()
    # example_minimal()
    # example_validation()

    print("Examples completed!")
    print("\nNote: Replace 'your-api-key-here' with your actual API key")
    print("and ensure you have sample files to test with.")
