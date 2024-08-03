import glob
import json
import logging
import os
import uuid

import cv2
import numpy as np
from pydantic_settings import BaseSettings
from kafka import KafkaProducer

from line_detector import detect_lines
from dlq_model import DLQModel

HANDLER_NAME = "Line Detector"


class Settings(BaseSettings):
    """Settings"""

    kafka_topic: str
    dlq_topic: str
    kafka_bootstrap_servers: str
    kafka_group_id: str = "line-detector"
    images_limit: int = 1000


def init_context(context):
    """Initializes nuclio context

    Args:
        context ([type]): Nuclio context
    """
    settings = Settings()
    context.logger.debug_with(
        f"Exporter initializing with:\n{settings.model_dump()}", handler=HANDLER_NAME
    )

    # Initialize Kafka producer with JSON serializer
    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: json.dumps(k).encode('utf-8') if k else None
    )
    setattr(context.user_data, "kafka_topic", settings.kafka_topic)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)
    setattr(context.user_data, "kafka_producer", producer)
    setattr(context.user_data, "images_limit", settings.images_limit)


def http_handler(context, event):
    """Handles HTTP requests"""
    try:
        data = event.body
        images_count = 0

        logging.info(f"Data: {data}")

        # Check if 'input_folder' key exists in the data and is not empty
        if "input_folder" in data and data["input_folder"]:
            input_folder = data["input_folder"]
            image_files = glob.glob(os.path.join(input_folder, "*"))

            for image_file in image_files:
                images_limit = context.user_data.images_limit
                if images_count >= images_limit:
                    context.logger.info(
                        f"Reached maximum number of images: {images_limit}"
                    )
                    break

                with open(image_file, "rb") as f:
                    image_data = f.read()

                context.logger.info(f"Processing image: {image_file}")
                process_image(context, image_data)
                images_count += 1

            context.logger.info(f"Processed {len(image_files)} images")

        # If 'input_folder' key doesn't exist, check for 'image_path' key
        elif "image_path" in data and data["image_path"]:
            image_path = data["image_path"]
            context.logger.info(f"Processing single image: {image_path}")
            with open(image_path, "rb") as f:
                image_data = f.read()
            process_image(context, image_data)

        else:
            error_message = "No image data or input folder in request"
            context.logger.error(error_message)
            dlq_model = DLQModel(
                source="line_detector",
                message=error_message,
                value=data
            )
            context.user_data.kafka_producer.send(
                context.user_data.dlq_topic,
                value=dlq_model.model_dump()
            )
            return context.Response(
                body=error_message,
                status_code=400,
                content_type="text/plain"
            )

        context.logger.info("Processed request successfully")

    except Exception as e:
        error_message = f"Error processing request: {str(e)}"
        context.logger.error(error_message)
        dlq_model = DLQModel(
            source="line_detector",
            message=error_message,
            value=data if 'data' in locals() else {}
        )
        context.user_data.kafka_producer.send(
            context.user_data.dlq_topic,
            value=dlq_model.model_dump()
        )
        return context.Response(
            body=error_message,
            status_code=500,
            content_type="text/plain"
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


def process_image(context, image_data):
    np_data = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(np_data, cv2.IMREAD_UNCHANGED)

    image_id = uuid.uuid4()

    lines = detect_lines(image)
    context.logger.info(f"Detected {len(lines)} lines for image: {image_id}")

    kafka_producer = context.user_data.kafka_producer

    if kafka_producer:
        kafka_producer.send(
            context.user_data.kafka_topic,
            value={"image_id": str(image_id), "lines": lines},
        )

    context.Response(
        body=f"Lines detected for image: {image_id}",
        headers={},
        content_type="text/plain",
    )