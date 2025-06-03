"""Generic Nuclio Handler Template"""

import logging
import multiprocessing as mp
import time
from kafka import KafkaProducer
import json
from pydantic_settings import BaseSettings
from common import ClassificationParams
from classification_orchestrator import ClassificationOrchestrator
from repository.image_repository import ImageRepository

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


def init_context(context):
    """Initializes Nuclio context

    Args:
        context: Nuclio context
    """

    context.logger.debug_with(
        f"Exporter initializing with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )
    settings = Settings()
    setattr(context.user_data, "kafka_topic", settings.kafka_topic)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)

    # Initialize multiprocessing settings
    try:
        mp.set_start_method("fork", force=True)
        context.logger.info_with(
            "Multiprocessing start method set to 'fork'", handler=HANDLER_NAME
        )
    except Exception as e:
        context.logger.warning_with(
            f"Could not set multiprocessing start method: {e}", handler=HANDLER_NAME
        )


def kafka_handler(context, event):
    """Handles HTTP requests"""
    start_time = time.time_ns()
    if isinstance(event.body, dict):
        data = event.body
    else:
        data = json.loads(event.body.decode("utf-8"))

    if data["operation"] != "classify":
        return

    image_id = data["parameters"]["image_id"]
    profiling = data["profiling"]
    delete_image_nodes = data["parameters"].get("delete_image_nodes", True)
    settings = Settings()

    classification_params_fields = {
        "ged_timeout",
    }

    params = {
        key: value
        for key, value in {
            **settings.model_dump(),
            **data["parameters"],
        }.items()
        if key in classification_params_fields
    }

    classification_params = ClassificationParams(**params)

    context.logger.info_with(
        f"Classification params: {classification_params}", handler=HANDLER_NAME
    )

    # Get orchestrator parameters
    use_multiprocessing = data["parameters"].get("use_multiprocessing", True)
    max_workers_override = data["parameters"].get("max_workers")

    # Create the classification orchestrator
    orchestrator = ClassificationOrchestrator(
        neo4j_dsn=settings.neo4j_dsn,
        neo4j_user=settings.neo4j_user,
        neo4j_pass=settings.neo4j_pass,
        ged_timeout=classification_params.ged_timeout,
        max_workers_override=max_workers_override,
        use_multiprocessing=use_multiprocessing,
    )

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    try:
        if not image_id:
            raise ValueError("image_id must be provided in the request body")

        # Perform classification using orchestrator
        comparison_results = orchestrator.classify_image(image_id)

        context.logger.info_with(
            f"Classification results: {len(comparison_results)} matches found",
            handler=HANDLER_NAME,
        )

        profiling["classification_time_ms"] = (time.time_ns() - start_time) / 1_000_000
        producer.send(
            context.user_data.kafka_topic,
            value={
                "status": "success",
                "classification_results": [
                    result.__dict__ for result in comparison_results
                ],
                "image_id": image_id,
                "image_path": data["parameters"]["image_path"],
                "parameters": {**params, **data["parameters"]},
                "profiling": profiling,
            },
        )

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        logging.error(f"Error: {e}", exc_info=True, stack_info=True)

        producer.send(
            context.user_data.dlq_topic,
            value={"error": str(e), "source": HANDLER_NAME, "value": data},
        )

    finally:
        if delete_image_nodes:
            image_repository = ImageRepository(
                settings.neo4j_dsn,
                settings.neo4j_user,
                settings.neo4j_pass,
            )
            image_repository.remove_image_nodes(image_id)
            image_repository.close()
        producer.close()


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
