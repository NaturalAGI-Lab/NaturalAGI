import json
import traceback
import uuid

from kafka import KafkaProducer
from pydantic_settings import BaseSettings

from service.graph_persistance_service import GraphPersistenceService
from converter.graph_serializer import GraphDeserializer
from dto.dlq_model import DLQModel
from data_preprocessing_service import DataPreprocessingService
from networkx_graph_analysis import NetworkxGraphAnalysis

HANDLER_NAME = "Contour analysis"


class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    next_nuclio: str = ""
    dlq_topic: str
    kafka_bootstrap_servers: str


def init_context(context):
    """Initializes nuclio context

    Args:
        context ([type]): Nuclio context
    """
    settings = Settings()
    context.logger.debug_with(
        f"Exporter initializing with:\n{settings.model_dump()}", handler=HANDLER_NAME
    )

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    graph_persistence_service = GraphPersistenceService(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    data_preprocessing_service = DataPreprocessingService(graph_persistence_service)
    setattr(context.user_data, "data_preprocessing_service", data_preprocessing_service)
    setattr(context.user_data, "next_nuclio", settings.next_nuclio)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)
    setattr(context.user_data, "kafka_producer", producer)


def kafka_handler(context, event):
    """Handles Kafka messages"""
    try:
        context.logger.info_with(
            f"New event received: {event.trigger.kind}", handler=HANDLER_NAME
        )
        input_data = json.loads(event.body)

        operation = input_data["operation"]
        parameters = input_data["parameters"]

        context.logger.info_with(f"Operation: {operation}", handler=HANDLER_NAME)
        context.logger.info_with(f"Parameters: {parameters}", handler=HANDLER_NAME)

        network = GraphDeserializer.deserialize(input_data["skeleton"])
        context.user_data.data_preprocessing_service.persist_graph(
            network, str(uuid.uuid4()), parameters["session_id"]
        )
        # NetworkxGraphAnalysis(network).analyze_graph()
    except Exception as e:
        send_to_dlq(context, input_data, str(e))
        traceback.print_exc()


def handler(context, event):
    """Nuclio handler"""

    context.logger.info_with(
        f"Got request: {event.trigger.kind} {event.content_type}", handler=HANDLER_NAME
    )
    context.logger.info_with(
        f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME
    )

    if event.trigger.kind == "kafka-cluster":
        kafka_handler(context, event)

    else:
        context.logger.error_with(
            "Unknown trigger. Expected kafka or http", handler=HANDLER_NAME
        )


def send_to_dlq(context, value, error):
    """Sends to DLQ"""
    context.logger.error_with(f"Error: {error}", handler=HANDLER_NAME)
    traceback.print_exc()

    dlq_model = DLQModel(source=HANDLER_NAME, message=error, value=value)
    context.user_data.kafka_producer.send(
        context.user_data.dlq_topic, value=dlq_model.model_dump()
    )
