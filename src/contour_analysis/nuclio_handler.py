import json
import traceback

from kafka import KafkaProducer
from pydantic_settings import BaseSettings

from common import DLQModel
from service.graph_persistance_service import GraphPersistenceService
from converter.graph_serializer import GraphDeserializer
from data_preprocessing_service import DataPreprocessingService
from networkx_graph_analysis import NetworkxGraphAnalysis
from service.visitor_result_persistence_service import VisitorResultPersistenceService
from logic.tertiary_features.tertiary_features_service import TertiaryFeaturesService
from service.analysis_result_persistence_service import AnalysisResultPersistenceService
from service.graph_analysis.analyzers.contour_type_analyzer import ContourTypeAnalyzer
from service.graph_analysis.analyzers.monotony_analyzer import MonotonyAnalyzer
from service.graph_analysis.analyzers.cycle_count_analyzer import CycleCountAnalyzer
from service.graph_analysis.analyzers.graph_metrics_analyzer import GraphMetricsAnalyzer
from service.graph_analysis.analyzers.curve_analyzer import CurveAnalyzer
from visitors.relative_position_visitor import RelativePositionVisitor
from visitors.angle_visitor import AngleVisitor
from visitors.half_plane_visitor import HalfPlaneVisitor
from visitors.quadrant_visitor import QuadrantVisitor

HANDLER_NAME = "Contour analysis"


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

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    graph_persistence_service = GraphPersistenceService(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    visitor_result_persistence_service = VisitorResultPersistenceService(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    data_preprocessing_service = DataPreprocessingService(graph_persistence_service)
    tertiary_features_service = TertiaryFeaturesService(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    analysis_result_persistence_service = AnalysisResultPersistenceService(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    setattr(context.user_data, "tertiary_features_service", tertiary_features_service)
    setattr(context.user_data, "data_preprocessing_service", data_preprocessing_service)
    setattr(
        context.user_data,
        "visitor_result_persistence_service",
        visitor_result_persistence_service,
    )
    setattr(
        context.user_data,
        "analysis_result_persistence_service",
        analysis_result_persistence_service,
    )
    setattr(context.user_data, "next_nuclio", settings.next_nuclio)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)
    setattr(context.user_data, "kafka_producer", producer)
    setattr(context.user_data, "settings", settings)
    setattr(context.user_data, "kafka_topic", settings.kafka_topic)


def kafka_handler(context, event):
    """Handles Kafka messages"""
    try:
        context.logger.info_with(
            f"New event received: {event.trigger.kind}", handler=HANDLER_NAME
        )
        input_data = json.loads(event.body)

        operation = input_data["operation"]
        parameters = input_data["parameters"]
        session_id = parameters["session_id"]
        image_id = parameters["image_id"]

        context.logger.info_with(f"Operation: {operation}", handler=HANDLER_NAME)
        context.logger.info_with(f"Parameters: {parameters}", handler=HANDLER_NAME)

        network = GraphDeserializer.deserialize(input_data["skeleton"])

        # Create NetworkxGraphAnalysis instance
        networkx_graph_analysis = NetworkxGraphAnalysis(
            network,
            visitor_result_persistence_service=context.user_data.visitor_result_persistence_service,
            analysis_result_persistence_service=context.user_data.analysis_result_persistence_service,
            merge_threshold=context.user_data.settings.merge_threshold,
        )

        # Apply reduction rules first
        networkx_graph_analysis.merge_close_intersection_points()

        # Now persist the graph AFTER merging operations
        context.user_data.data_preprocessing_service.persist_graph(
            network, image_id, parameters["session_id"]
        )

        # Continue with the rest of the analysis
        networkx_graph_analysis.add_visitor(QuadrantVisitor())
        # networkx_graph_analysis.add_visitor(LengthComparisonVisitor())
        networkx_graph_analysis.add_visitor(AngleVisitor(network))
        networkx_graph_analysis.add_visitor(HalfPlaneVisitor(network))
        networkx_graph_analysis.add_visitor(
            RelativePositionVisitor(
                network, parameters["image_width"], parameters["image_height"]
            )
        )

        networkx_graph_analysis.add_analyzer(ContourTypeAnalyzer)
        networkx_graph_analysis.add_analyzer(MonotonyAnalyzer)
        networkx_graph_analysis.add_analyzer(CycleCountAnalyzer)
        networkx_graph_analysis.add_analyzer(GraphMetricsAnalyzer)
        # networkx_graph_analysis.add_analyzer(CurveAnalyzer)
        networkx_graph_analysis.analyze_graph(image_id, session_id)

        context.user_data.tertiary_features_service.create_tertiary_features(
            image_id, session_id
        )

        context.user_data.kafka_producer.send(
            context.user_data.kafka_topic,
            value={"operation": operation, "parameters": parameters},
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
        context.user_data.dlq_topic, value=dlq_model.model_dump()
    )
