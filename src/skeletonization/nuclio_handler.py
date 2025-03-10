"""Generic Nuclio Handler Template"""

import json
import cv2
from kafka import KafkaProducer
import traceback
from common import DLQModel
from settings import Settings
from skeleton_gng_mapper import SkeletonGNGMapper
from graph_serializer import GraphSerializer


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
    
    # Get JSON from the event.body
    data = json.loads(event.body)
    try:

        context.logger.info_with(
            f"Received request: {data}", handler=HANDLER_NAME
        )
        
        operation = data.get('operation')
        parameters = data.get('parameters', {})
        
        context.logger.info_with(f"Received request: {event.trigger.kind}", handler=HANDLER_NAME)
        context.logger.info_with(f"Operation: {operation}", handler=HANDLER_NAME)
        context.logger.info_with(f"Parameters: {parameters}", handler=HANDLER_NAME)

        image = cv2.imread(parameters["image_path"], 0)
        
        image_width = image.shape[1]
        image_height = image.shape[0]
        
        parameters["image_width"] = image_width
        parameters["image_height"] = image_height
        
        settings = Settings()
        skeletonization_threshold = parameters.get("skeletonization_threshold", settings.skeletonization_threshold)
        simplification_epsilon = parameters.get("simplification_epsilon", settings.simplification_epsilon)
        net, threshold = SkeletonGNGMapper(context, settings, skeletonization_threshold, simplification_epsilon).process_image(image)
        data["parameters"]["skeletonization_threshold"] = threshold
        data["parameters"]["simplification_epsilon"] = simplification_epsilon
        
        json_net = GraphSerializer.serialize(net)
        context.logger.info_with(f"Net: {json_net}", handler=HANDLER_NAME)

        context.logger.info_with(
            "Processed request successfully", handler=HANDLER_NAME
        )
        data["skeleton"] = json_net
        context.user_data.kafka_producer.send(
            context.user_data.kafka_topic,
            value=data
        )

    except Exception as e:
        context.logger.warn_with(f"Error: {e}", handler=HANDLER_NAME)
        traceback.print_exc()

        dlq_model = DLQModel(
            source=HANDLER_NAME,
            error= {
                "error": str(e),
                "traceback": traceback.format_exc()
            },
            value=data
        )
        context.user_data.kafka_producer.send(
            context.user_data.dlq_topic,
            value=dlq_model.model_dump()
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