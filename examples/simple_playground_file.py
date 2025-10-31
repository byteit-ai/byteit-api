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
    api_key="36348b5a-3688-46a0-a735-6bd81965a266.26ee01dd17e93b907d3cb3a92ed46ac0398a124ea5eca1ff2cbc4fd4f613dcb3"
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
