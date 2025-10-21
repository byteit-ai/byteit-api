#!/usr/bin/env python3
"""
Example: Process multiple file types using ByteIT library.

This script demonstrates how to process different document types
(PDF, DOCX, images, etc.) using the same LocalFileInputConnector.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import byteit
sys.path.insert(0, str(Path(__file__).parent.parent))

from byteit import ByteITClient
from byteit.connectors import LocalFileInputConnector
from byteit.exceptions import ByteITError


def process_file(
    client: ByteITClient, file_path: str, output_format: str = "md"
):
    """
    Process a single file and save the result.

    Args:
        client: ByteIT client instance
        file_path: Path to the file to process
        output_format: Desired output format (txt, md, json, html)
    """
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        print(f"  ✗ File not found: {file_path}")
        return

    print(f"\n  Processing: {file_path_obj.name}")

    try:
        # Create input connector (automatically detects file type)
        input_connector = LocalFileInputConnector(file_path=str(file_path_obj))

        # Create output filename based on input
        output_file = file_path_obj.stem + f"_output.{output_format}"

        # Process the document
        result_path = client.process_document(
            input_connector=input_connector,
            processing_options={"output_format": output_format},
            output_path=output_file,
            poll_interval=2,
            max_wait_time=300,
        )

        print(f"  ✓ Success! Saved to: {result_path}")

        # Show file size
        output_size = Path(result_path).stat().st_size
        print(f"  Output size: {output_size:,} bytes")

    except FileNotFoundError as e:
        print(f"  ✗ Error: {e}")
    except ByteITError as e:
        print(f"  ✗ ByteIT Error: {e}")
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")


def main():
    """Process multiple files of different types."""
    # Get API key from environment
    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: Please set BYTEIT_API_KEY environment variable")
        print("Example: export BYTEIT_API_KEY='your-api-key'")
        return

    print("=" * 60)
    print("ByteIT Multi-File Processing Example")
    print("=" * 60)

    # Example files to process (replace with your actual files)
    files_to_process = [
        ("document1.pdf", "md"),  # PDF to Markdown
        ("document2.docx", "txt"),  # DOCX to Text
        ("scanned_page.jpg", "json"),  # Image to JSON
        ("report.pdf", "html"),  # PDF to HTML
    ]

    # Initialize client with context manager
    with ByteITClient(api_key=api_key) as client:
        print("\nStarting batch processing...")

        successful = 0
        failed = 0

        for file_path, output_format in files_to_process:
            try:
                process_file(client, file_path, output_format)
                successful += 1
            except Exception:
                failed += 1

        # Summary
        print("\n" + "=" * 60)
        print("Processing Summary")
        print("=" * 60)
        print(f"Total files: {len(files_to_process)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")


def process_directory():
    """Example: Process all PDF files in a directory."""
    print("\n" + "=" * 60)
    print("Directory Processing Example")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: Please set BYTEIT_API_KEY environment variable")
        return

    # Get directory from command line or use current directory
    if len(sys.argv) > 1:
        directory = Path(sys.argv[1])
    else:
        directory = Path(".")

    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory")
        return

    print(f"\nScanning directory: {directory.absolute()}")

    # Find all PDF files
    pdf_files = list(directory.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in the directory")
        return

    print(f"Found {len(pdf_files)} PDF file(s)")

    with ByteITClient(api_key=api_key) as client:
        for pdf_file in pdf_files:
            process_file(client, str(pdf_file), output_format="md")


def interactive_mode():
    """Interactive mode: Ask user for file path and process it."""
    print("\n" + "=" * 60)
    print("Interactive File Processing")
    print("=" * 60)

    api_key = os.environ.get("BYTEIT_API_KEY")
    if not api_key:
        print("Error: Please set BYTEIT_API_KEY environment variable")
        return

    with ByteITClient(api_key=api_key) as client:
        while True:
            print("\n" + "-" * 60)
            file_path = input("Enter file path (or 'quit' to exit): ").strip()

            if file_path.lower() in ("quit", "q", "exit"):
                print("Goodbye!")
                break

            if not file_path:
                continue

            # Ask for output format
            print("\nOutput formats: txt, md, json, html")
            output_format = (
                input("Enter output format (default: md): ").strip() or "md"
            )

            if output_format not in ("txt", "md", "json", "html"):
                print(f"Invalid format '{output_format}', using 'md'")
                output_format = "md"

            process_file(client, file_path, output_format)


if __name__ == "__main__":
    print("\nChoose a mode:")
    print("1. Process predefined files")
    print("2. Process all PDFs in a directory")
    print("3. Interactive mode")

    choice = input("\nEnter your choice (1-3): ").strip()

    if choice == "1":
        main()
    elif choice == "2":
        process_directory()
    elif choice == "3":
        interactive_mode()
    else:
        print("Invalid choice. Running default mode...")
        main()
