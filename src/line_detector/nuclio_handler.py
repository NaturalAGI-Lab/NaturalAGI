import base64
import traceback

import requests
import numpy as np
import cv2
import uuid
from lines_repository import LinesRepository
from line_detector import LineDetector

from pydantic_settings import BaseSettings


HANDLER_NAME = "Line Detector"


class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    next_nuclio: str = ""


def init_context(context):
    """Initializes nuclio context

    Args:
        context ([type]): Nuclio context
    """
    context.logger.debug_with(
        f"Exporter initializing with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )

    lines_repository = LinesRepository(Settings().neo4j_dsn, Settings().neo4j_user, Settings().neo4j_pass)
    setattr(context.user_data, "lines_repository", lines_repository)
    
    setattr(context.user_data, "next_nuclio", Settings().next_nuclio)


def http_handler(context, event):
    """Handles HTTP requests"""
    try:
        data = event.body

        decoded_data = base64.b64decode(data['image'])
        np_data = np.fromstring(decoded_data, np.uint8)
        image = cv2.imdecode(np_data, cv2.IMREAD_UNCHANGED)
        
        image_id = uuid.uuid4()
        
        lines = LineDetector().detect_lines(image)
        result = context.user_data.lines_repository.add_lines(lines, image_id)
        print(f"Result adding lines: {result}")
        
        next_functions_str = context.user_data.next_nuclio

        if next_functions_str:
            next_nuclio = next_functions_str.split(";")
            context.logger.debug_with(f"Next functions: {next_nuclio}", handler=HANDLER_NAME)

            if len(next_nuclio) > 0:
                for func in next_nuclio:
                    context.logger.info_with(f"Calling {func}", handler=HANDLER_NAME)
                    requests.post(func, json=str(image_id))

        context.Response(
            body=f"Lines detected for image: {image_id}",
            headers={},
            content_type="text/plain",
            status_code=requests.codes.ok,  # pylint: disable=no-member
        )

    except Exception as e:
        context.logger.error_with(
            f"Error:\n {e}", handler=HANDLER_NAME
        )
        traceback.print_exc()

        context.Response(
            body=f"Error detecting lines for image: {e}",
            headers={},
            content_type="text/plain",
            status_code=requests.codes.server_error,  # pylint: disable=no-member
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
