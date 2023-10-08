"""Image Exporter Nuclio Handler"""
import json
import os
import base64
import io
import traceback

import requests
import cv2
import numpy as np

from pydantic_settings import BaseSettings

from image_to_neo_exporter import ImageNeoExporter


HANDLER_NAME = "Image Exporter"


class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    handler_name = HANDLER_NAME


def init_context(context):
    """Initializes nuclio context

    Args:
        context ([type]): Nuclio context
    """
    

    exporter = ImageNeoExporter(Settings().neo4j_dsn, Settings().neo4j_user, Settings().neo4j_pass)
    setattr(context.user_data, "exporter", exporter)

    context.logger.debug_with(
        f"Exporter initialized with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )


def http_handler(context, event):
    """Handles HTTP requests"""
    
    data = event.body
    
    context.logger.debug_with(
        f"Received data:\n{data}", handler=HANDLER_NAME
    )
    
    buf = io.BytesIO(base64.b64decode(data["image"]))
    npimg = np.frombuffer(buf, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_UNCHANGED)
    
    context.logger.debug_with(
        f"Received image:\n{img.shape}", handler=HANDLER_NAME
    )
    
    context.Response(
        body="Received a http request - nothing to do",
        headers={},
        content_type="text/plain",
        status_code=requests.codes.ok,  # pylint: disable=no-member
    )



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
