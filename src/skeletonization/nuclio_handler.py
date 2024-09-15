"""Generic Nuclio Handler Template"""

import json
from kafka import KafkaProducer
import traceback
from src.skeletonization.skeleton_points_repository import calculate_angle_points
from pydantic_settings import BaseSettings
from dlq_model import DLQModel

HANDLER_NAME = "angle_point_detector"


class Settings(BaseSettings):
    """Settings"""
    kafka_topic: str
    dlq_topic: str 
    kafka_bootstrap_servers: str
    kafka_group_id: str = "growing-neural-gas"


def init_context(context):
    """Initializes Nuclio context

    Args:
        context: Nuclio context
    """
    settings = Settings()
    context.logger.debug_with(
        f"Exporter initializing with:\n{settings.model_dump()}", handler=HANDLER_NAME
    )
    
    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    setattr(context.user_data, "kafka_topic", settings.kafka_topic)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)
    setattr(context.user_data, "kafka_producer", producer)


def kafka_handler(context, event):
    """Handles Kafka messages"""
    try:
        # Get JSON from the event.body
        line_detector_results = json.loads(event.body)

        context.logger.info_with(
            f"Received request: {line_detector_results}", handler=HANDLER_NAME
        )

        lines = line_detector_results["lines"]
        context.logger.info_with(f"Lines: {lines}", handler=HANDLER_NAME)

        angle_points = calculate_angle_points(lines)

        context.logger.info_with(
            f"Angle points: {angle_points}", handler=HANDLER_NAME
        )

        # Merge angle points with line detector results
        line_detector_results["angle_points"] = angle_points

        if False: #len(angle_points) < 3:
            context.logger.warn_with(
                f"Detected {len(angle_points)} angle points, expected at least 3. Sending to DLQ.",
                handler=HANDLER_NAME
            )
            dlq_model = DLQModel(
                source=HANDLER_NAME,
                message="Invalid number of angle points",
                value=line_detector_results
            )
            context.user_data.kafka_producer.send(
                context.user_data.dlq_topic,
                value=dlq_model.model_dump()
            )
        else:
            context.logger.info_with(
                "Processed request successfully", handler=HANDLER_NAME
            )
            context.user_data.kafka_producer.send(
                context.user_data.kafka_topic,
                value=line_detector_results
            )

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        traceback.print_exc()

        dlq_model = DLQModel(
            source=HANDLER_NAME,
            message=str(e),
            value=line_detector_results if 'line_detector_results' in locals() else {}
        )
        context.user_data.kafka_producer.send(
            context.user_data.dlq_topic,
            value=dlq_model.model_dump()
        )

        context.Response(
            body=f"Error: {e}",
            headers={},
            content_type="text/plain",
            status_code=500,
        )


def handler(context, event):
    """Nuclio main handler"""

    context.logger.info_with(
        f"Received request: {event.trigger.kind}", handler=HANDLER_NAME
    )
    context.logger.info_with(
        f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME
    )

    if event.trigger.kind == "kafka-cluster":
        kafka_handler(context, event)
    else:
        context.logger.error_with(
            "Unknown trigger. Only HTTP supported", handler=HANDLER_NAME
        )