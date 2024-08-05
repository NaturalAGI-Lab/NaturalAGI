import json
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


def handler(context, event):
    """Nuclio handler"""
    try:
        context.logger.info_with(
            f"Got request: {event.trigger.kind}", handler=HANDLER_NAME
        )

        if event.trigger.kind == "kafka-cluster":
            message = json.loads(event.body.decode('utf-8'))
            process_image(context, message)
        else:
            raise ValueError("Unknown trigger. Expected kafka-cluster")

    except Exception as e:
        context.logger.error_with(f"Error processing message: {e}", handler=HANDLER_NAME)
        dlq_model = DLQModel(
            source=HANDLER_NAME,
            message=str(e),
            value=event.body.decode('utf-8')
        )
        context.user_data.kafka_producer.send(
            context.user_data.dlq_topic,
            value=dlq_model.model_dump()
        )


def process_image(context, message):
    operation = message.get('operation')
    parameters = message.get('parameters', {})
    image_path = parameters.get('image_path')

    if not image_path:
        raise ValueError("Image path not provided in the message")

    with open(image_path, "rb") as f:
        image_data = f.read()

    np_data = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(np_data, cv2.IMREAD_UNCHANGED)

    image_id = uuid.uuid4()

    lines = detect_lines(image)
    context.logger.info(f"Detected {len(lines)} lines for image: {image_id}")

    kafka_producer = context.user_data.kafka_producer

    if kafka_producer:
        kafka_producer.send(
            context.user_data.kafka_topic,
            value={
                "operation": operation,
                "image_id": str(image_id),
                "lines": lines,
                "parameters": parameters
            },
        )

    context.logger.info(f"Lines detected for image: {image_id}")