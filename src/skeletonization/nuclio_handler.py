"""Generic Nuclio Handler Template"""

import json
from kafka import KafkaProducer
import traceback
from src.skeletonization.skeleton_points_repository import calculate_angle_points
from dlq_model import DLQModel
from settings import Settings
from skeletonization import gng_skeletonization, net_to_json

HANDLER_NAME = "skeletonization"


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
        body = json.loads(event.body)

        context.logger.info_with(
            f"Received request: {body}", handler=HANDLER_NAME
        )

        net = gng_skeletonization(body["image_path"], Settings())
        json_net = net_to_json(net)
        context.logger.info_with(f"Net: {json_net}", handler=HANDLER_NAME)

        if False: 
            pass
        else:
            context.logger.info_with(
                "Processed request successfully", handler=HANDLER_NAME
            )
            context.user_data.kafka_producer.send(
                context.user_data.kafka_topic,
                value=json_net
            )

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        traceback.print_exc()

        dlq_model = DLQModel(
            source=HANDLER_NAME,
            message=str(e),
            value=json_net if 'json_net' in locals() else {}
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