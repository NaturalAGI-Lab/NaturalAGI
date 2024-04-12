import base64
import os
import glob

import requests
import numpy as np
import cv2
import uuid
from lines_repository import LinesRepository
from line_detector import LineDetector

from pydantic_settings import BaseSettings


HANDLER_NAME = "Line Detector"
MAX_IMAGES = float("inf")


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

    lines_repository = LinesRepository(
        Settings().neo4j_dsn, Settings().neo4j_user, Settings().neo4j_pass
    )
    setattr(context.user_data, "lines_repository", lines_repository)

    setattr(context.user_data, "next_nuclio", Settings().next_nuclio)


def http_handler(context, event):
    """Handles HTTP requests"""
    try:
        data = event.body
        images_count = 0

        # Check if 'input_folder' key exists in the data and is not empty
        if "input_folder" in data and data["input_folder"]:
            input_folder = data["input_folder"]
            image_files = glob.glob(os.path.join(input_folder, "*"))

            for image_file in image_files:
                if images_count >= MAX_IMAGES:
                    context.logger.info(
                        f"Reached maximum number of images: {MAX_IMAGES}"
                    )
                    break

                with open(image_file, "rb") as f:
                    image_data = f.read()

                context.logger.info(f"Processing image: {image_file}")
                process_image(context, image_data)
                images_count += 1

            context.logger.info(f"Processed {len(image_files)} images")

        # If 'input_folder' key doesn't exist, check for 'image' key
        elif "image" in data and data["image"]:
            image_data = base64.b64decode(data["image"])
            process_image(context, image_data)

        else:
            context.logger.error("No image data or input folder in request")
            return

        context.logger.info("Processed request successfully")

    except Exception as e:
        context.logger.error(f"Error processing request: {str(e)}")


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


def process_image(context, image_data):
    np_data = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(np_data, cv2.IMREAD_UNCHANGED)

    image_id = uuid.uuid4()

    lines = LineDetector().detect_lines(image)
    context.logger.info(f"Detected {len(lines)} lines for image: {image_id}")
    context.user_data.lines_repository.add_lines(lines, image_id)

    next_functions_str = context.user_data.next_nuclio

    if next_functions_str:
        next_nuclio = next_functions_str.split(";")
        context.logger.debug_with(
            f"Next functions: {next_nuclio}", handler=HANDLER_NAME
        )

        if len(next_nuclio) > 0:
            for func in next_nuclio:
                context.logger.info_with(f"Calling {func}", handler=HANDLER_NAME)
                response = requests.post(func, json=str(image_id))
                context.logger.info_with(
                    f"Response: {response.status_code}", handler=HANDLER_NAME
                )

    context.Response(
        body=f"Lines detected for image: {image_id}",
        headers={},
        content_type="text/plain",
    )
