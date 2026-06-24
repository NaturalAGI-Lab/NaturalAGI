import json
import dataclasses
import traceback
import time

from kafka import KafkaProducer
from neo4j import GraphDatabase
from pydantic_settings import BaseSettings

from common.model import DLQModel
from common.tracing import init_tracer, inject_trace_headers, extract_trace_context, SpanKind
from service.graph_persistance_service import GraphPersistenceService
from converter.graph_serializer import GraphDeserializer
from data_preprocessing_service import DataPreprocessingService
from networkx_graph_analysis import NetworkxGraphAnalysis
from logic.tertiary_features.tertiary_features_service import TertiaryFeaturesService
from service.analysis_result_persistence_service import AnalysisResultPersistenceService
from service.graph_analysis.analyzers.contour_type_analyzer import ContourTypeAnalyzer
from service.graph_analysis.analyzers.monotony_analyzer import MonotonyAnalyzer
from service.graph_analysis.analyzers.cycle_count_analyzer import CycleCountAnalyzer
from service.graph_analysis.analyzers.structural_feature_analyzer import StructuralFeatureAnalyzer

HANDLER_NAME = "contour_analysis"


class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    next_nuclio: str = ""
    dlq_topic: str
    kafka_topic: str
    kafka_bootstrap_servers: str
    merge_threshold: float = (
        10.0  # Default threshold for merging close intersection points
    )


def init_context(context):
    """Initializes nuclio context

    Args:
        context ([type]): Nuclio context
    """
    settings = Settings()
    context.logger.debug_with(
        f"Exporter initializing with:\n{settings.model_dump()}", handler=HANDLER_NAME
    )

    driver = GraphDatabase.driver(
        settings.neo4j_dsn, auth=(settings.neo4j_user, settings.neo4j_pass)
    )
    graph_persistence_service = GraphPersistenceService(driver)
    data_preprocessing_service = DataPreprocessingService(graph_persistence_service)
    tertiary_features_service = TertiaryFeaturesService(driver)
    analysis_result_persistence_service = AnalysisResultPersistenceService(driver)

    setattr(
        context.user_data, "kafka_bootstrap_servers", settings.kafka_bootstrap_servers
    )
    setattr(context.user_data, "tertiary_features_service", tertiary_features_service)
    setattr(context.user_data, "data_preprocessing_service", data_preprocessing_service)
    setattr(
        context.user_data,
        "analysis_result_persistence_service",
        analysis_result_persistence_service,
    )
    setattr(context.user_data, "next_nuclio", settings.next_nuclio)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)
    setattr(context.user_data, "settings", settings)
    setattr(context.user_data, "kafka_topic", settings.kafka_topic)

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    setattr(context.user_data, "kafka_producer", producer)

    tracer = init_tracer(HANDLER_NAME)
    setattr(context.user_data, "tracer", tracer)


def kafka_handler(context, event):
    """Handles Kafka messages"""
    try:
        start_time = time.time_ns()
        context.logger.info_with(
            f"New event received: {event.trigger.kind}", handler=HANDLER_NAME
        )
        input_data = json.loads(event.body)

        operation = input_data["operation"]
        parameters = input_data["parameters"]
        profiling = input_data["profiling"]
        session_id = parameters["session_id"]
        image_id = parameters["image_id"]

        tracing_disabled = bool(parameters.get("disable_tracing"))

        if not tracing_disabled:
            experiment_id = parameters.get("mlflow_experiment_id")
            if experiment_id:
                context.user_data.tracer = init_tracer(HANDLER_NAME, experiment_id)

        context.logger.info_with(f"Operation: {operation}", handler=HANDLER_NAME)
        context.logger.info_with(f"Parameters: {parameters}", handler=HANDLER_NAME)

        network = GraphDeserializer.deserialize(input_data["skeleton"])

        networkx_graph_analysis = NetworkxGraphAnalysis(
            network,
            analysis_result_persistence_service=context.user_data.analysis_result_persistence_service,
            merge_threshold=context.user_data.settings.merge_threshold,
        )

        networkx_graph_analysis.merge_close_intersection_points()

        context.user_data.data_preprocessing_service.persist_graph(
            network, image_id, parameters["session_id"], parameters.get("image_path")
        )

        networkx_graph_analysis.add_analyzer(ContourTypeAnalyzer)
        networkx_graph_analysis.add_analyzer(MonotonyAnalyzer)
        networkx_graph_analysis.add_analyzer(CycleCountAnalyzer)
        networkx_graph_analysis.add_analyzer(StructuralFeatureAnalyzer)
        networkx_graph_analysis.analyze_graph(image_id, session_id)

        context.user_data.tertiary_features_service.create_tertiary_features(
            image_id, session_id
        )

        profiling["contour_analysis_time_ms"] = (
            time.time_ns() - start_time
        ) / 1_000_000

        output_value = {
            "operation": operation,
            "parameters": parameters,
            "profiling": profiling,
        }

        if tracing_disabled:
            context.user_data.kafka_producer.send(
                context.user_data.kafka_topic,
                value=output_value,
                headers=[],
            )
        else:
            tracer = context.user_data.tracer
            parent_ctx = extract_trace_context(event.headers)
            with tracer.start_as_current_span(
                "contour_analysis.process", context=parent_ctx, kind=SpanKind.SERVER
            ) as span:
                span.set_attribute("image_id", image_id)
                span.set_attribute("session_id", session_id)
                if parameters.get("mlflow_run_id"):
                    span.set_attribute("mlflow.run_id", parameters["mlflow_run_id"])
                span.set_attribute("duration_ms", profiling["contour_analysis_time_ms"])

                headers = inject_trace_headers()
                context.user_data.kafka_producer.send(
                    context.user_data.kafka_topic,
                    value=output_value,
                    headers=headers,
                )

        context.logger.info_with(
            f"Analysis complete for image_id: {image_id}", handler=HANDLER_NAME
        )

    except Exception as error:
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }
        error_json = json.dumps(error_info)

        context.logger.error_with(
            "Error occurred during processing",
            handler=HANDLER_NAME,
            error_details=error_json,
        )
        send_to_dlq(context, input_data, error_info)


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

    dlq_model = DLQModel(source=HANDLER_NAME, error=error, value=value)
    context.user_data.kafka_producer.send(
        context.user_data.dlq_topic, value=dataclasses.asdict(dlq_model)
    )
