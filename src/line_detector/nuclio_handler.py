import json
import base64
import traceback

import requests
import cv2
import numpy as np
from image_repository import ImageRepository
from lines_repository import LinesRepository

from pydantic_settings import BaseSettings

from src.line_detector.line_detector import LineDetector

HANDLER_NAME = "Line Detector"


class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    next_nuclio = ""


def init_context(context):
    """Initializes nuclio context

    Args:
        context ([type]): Nuclio context
    """
    context.logger.debug_with(
        f"Exporter initializing with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )

    image_repository = ImageRepository(Settings().neo4j_dsn, Settings().neo4j_user, Settings().neo4j_pass)
    setattr(context.user_data, "image_repository", image_repository)

    lines_repository = LinesRepository(Settings().neo4j_dsn, Settings().neo4j_user, Settings().neo4j_pass)
    setattr(context.user_data, "lines_repository", lines_repository)


def http_handler(context, event):
    """Handles HTTP requests"""
    try:

        image_id = event.body

        context.logger.debug_with(f"Received image_id: {image_id}", handler=HANDLER_NAME)

        image = context.user_data.image_repository.get_image(image_id)
        lines = LineDetector.detect_lines(image)
        result = context.user_data.lines_repository.add_lines(lines, image_id)
        print(f"Result adding lines: {result}")

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
