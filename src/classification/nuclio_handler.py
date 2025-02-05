"""Generic Nuclio Handler Template"""

import logging
from kafka import KafkaProducer
import json
from pydantic_settings import BaseSettings
from graph_comparator import GraphComparator
from common import ClassificationParams

HANDLER_NAME = "classification"


class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    kafka_topic: str
    kafka_bootstrap_servers: str
    dlq_topic: str
    ged_timeout: float
    feature_weight: float
    structural_weight: float


def init_context(context):
    """Initializes Nuclio context

    Args:
        context: Nuclio context
    """

    context.logger.debug_with(
        f"Exporter initializing with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )
    settings = Settings()
    setattr(
        context.user_data,
        "kafka_producer",
        KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        ),
    )
    setattr(context.user_data, "kafka_topic", settings.kafka_topic)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)


def kafka_handler(context, event):
    """Handles HTTP requests"""
    # Parse the request body
    if isinstance(event.body, dict):
        data = event.body
    else:
        data = json.loads(event.body.decode("utf-8"))

    if data["operation"] != "classify":
        return

    image_id = data["parameters"]["image_id"]
    settings = Settings()
    
    # Filter only the parameters that ClassificationParams expects
    classification_params_fields = {
        "feature_weight",
        "structural_weight",
        "ged_timeout",
        # Add any other fields that ClassificationParams expects
    }
    
    # Create params dict with only the relevant fields
    params = {
        key: value 
        for key, value in {
            **settings.model_dump(),  # Get all settings as defaults
            **data["parameters"],     # Override with any provided parameters
        }.items()
        if key in classification_params_fields
    }
    
    classification_params = ClassificationParams(**params)
    
    context.logger.info_with(f"Classification params: {classification_params}", handler=HANDLER_NAME)
    comparator = GraphComparator(settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass, max_workers=10)

    try:
        if not image_id:
            raise ValueError("image_id must be provided in the request body")

        # Perform graph comparison
        comparison_results = comparator.compare_graphs(
            image_id, classification_params
        )

        context.logger.info_with(
            f"Classification results: {comparison_results}", handler=HANDLER_NAME
        )

        # Responding to the HTTP request
        context.user_data.kafka_producer.send(
            context.user_data.kafka_topic,
            value={
                "classification_results": comparison_results,
                "image_id": image_id,
                "image_path": data["parameters"]["image_path"],
            },
        )

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        logging.error(f"Error: {e}", exc_info=True, stack_info=True)

        context.user_data.kafka_producer.send(
            context.user_data.dlq_topic,
            value={"error": str(e)},
        )

    finally:
        # comparator.remove_image_nodes(image_id)
        comparator.close()


def handler(context, event):
    """Nuclio main handler"""

    context.logger.info_with(
        f"Received request: {event.trigger.kind}", handler=HANDLER_NAME
    )
    context.logger.info_with(
        f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME
    )

    if event.trigger.kind == "kafka-cluster":
        return kafka_handler(context, event)
    else:
        context.logger.error_with(
            "Unknown trigger. Only HTTP supported", handler=HANDLER_NAME
        )
