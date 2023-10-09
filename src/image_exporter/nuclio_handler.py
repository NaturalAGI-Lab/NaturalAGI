"""Image Exporter Nuclio Handler"""
import json
import os
import base64
import io
import traceback
from PIL import Image

import requests
import cv2
import numpy as np

from pydantic_settings import BaseSettings

from image_to_neo_exporter import ImageNeoExporter
from nuclio_sdk import Event


HANDLER_NAME = "Image Exporter"


class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str


def init_context(context):
    """Initializes nuclio context

    Args:
        context ([type]): Nuclio context
    """
    
    context.logger.debug_with(
        f"Exporter initializing with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )

    exporter = ImageNeoExporter(Settings().neo4j_dsn, Settings().neo4j_user, Settings().neo4j_pass)
    setattr(context.user_data, "exporter", exporter)

    


def http_handler(context, event):
    """Handles HTTP requests"""
    try: 
    
        data = event.body
        
        # context.logger.debug_with(
        #     f"Received data:\n{data}", handler=HANDLER_NAME
        # )
        
        
        buf = io.BytesIO(base64.b64decode(data))
        # npimg = np.frombuffer(buf, np.uint8)
        # img = cv2.imdecode(npimg, cv2.IMREAD_UNCHANGED)
        
        image = Image.open(buf)
        
        context.logger.debug_with(
            f"Received image:\n{image.size}", handler=HANDLER_NAME
        )
        
        context.Response(
            body="Received a http request - nothing to do",
            headers={},
            content_type="text/plain",
            status_code=requests.codes.ok,  # pylint: disable=no-member
        )
    
    except Exception as e:
        context.logger.error_with(
            f"Error:\n {e}", handler=HANDLER_NAME
        )
        traceback.print_exc()



def handler(context, event):
    """Nuclio handler"""

    context.logger.info_with(
        f"Got request: {event.trigger.kind} {event.content_type}", handler=HANDLER_NAME
    )
    context.logger.info_with(
        f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME
    )

    if event.trigger.kind == "http":
        http_handler(context, event)

    else:
        context.logger.error_with(
            "Unknown trigger. Expected kafka or http", handler=HANDLER_NAME
        )
