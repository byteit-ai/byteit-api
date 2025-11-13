# Parent directory to path to import byteit
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from byteit import ByteITClient
from byteit.connectors import (
    LocalFileInputConnector,
    S3InputConnector,
    S3OutputConnector,
)

client = ByteITClient(
    api_key="5210fd96-aacd-4792-8326-2ffe9acd2ed9.424d59ee375ca6d42e5826d98b5105fa3504234cf9fe08a457e54381253446e9"
)

client.create_job(
    nickname="Simplest Usecase local file",
    input_connector=LocalFileInputConnector(file_path="sample_document.pdf"),
    # nickname="Simplest Usecase S3 to S3",
    # input_connector=S3InputConnector(
    #     source_bucket="company-processed-byteit",
    #     source_path_inside_bucket="input/2.pdf",
    # ),
    # output_connector=S3OutputConnector(
    #     bucket="company-processed-byteit",
    #     path="output/",
    # ),
)
