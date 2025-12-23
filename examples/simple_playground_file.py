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
    api_key="a40c7fe9-44fb-4d70-9ce5-aab478f187d7.36c5492be4253bdb875a366da62a6f4cdf6e2505e3b141a7c13a2cb789b968a9"
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
