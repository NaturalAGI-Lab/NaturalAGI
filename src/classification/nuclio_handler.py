"""Generic Nuclio Handler Template"""

import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Optional

from kafka import KafkaProducer
from pydantic_settings import BaseSettings
from opentelemetry import trace as otel_trace
from common.tracing import init_tracer, extract_trace_context
from classification_orchestrator import ClassificationOrchestrator
from graph_similarity import cost_functions as _cf
from repository.concept_repository import ConceptRepository
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
    skeletonization_threshold: float = 180.0
    simplification_epsilon: Optional[float] = None
    comparison_method: str = "ged"
    fgw_alpha: float = 0.5


@contextmanager
def _cost_config_override(features=None, normalizers=None, costs=None):
    orig_features = _cf.features
    orig_normalizers = _cf.PROPERTY_NORMALIZERS
    orig_costs = {k: v for k, v in vars(_cf.NodeCost).items() if not k.startswith("_")}
    try:
        if features is not None:
            _cf.features = features
        if normalizers is not None:
            _cf.PROPERTY_NORMALIZERS = normalizers
        if costs is not None:
            for k, v in costs.items():
                setattr(_cf.NodeCost, k.upper(), float(v))
        yield
    finally:
        _cf.features = orig_features
        _cf.PROPERTY_NORMALIZERS = orig_normalizers
        for k, v in orig_costs.items():
            setattr(_cf.NodeCost, k, v)


def init_context(context):
    """Initializes Nuclio context

    Args:
        context: Nuclio context
    """

    settings = Settings()
    context.logger.debug_with(
        f"Exporter initializing with:\n{settings.model_dump()}", handler=HANDLER_NAME
    )
    setattr(context.user_data, "settings", settings)
    setattr(context.user_data, "kafka_topic", settings.kafka_topic)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    setattr(context.user_data, "kafka_producer", producer)

    concept_repo = ConceptRepository(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    concept_ids = concept_repo.get_all_concept_ids()
    concept_graphs = {
        cid: concept_repo.get_concept_graph(cid) for cid in concept_ids
    }
    concept_repo.close()
    setattr(context.user_data, "concept_graphs", concept_graphs)
    context.logger.info_with(
        f"Cached {len(concept_graphs)} concept graphs at startup",
        handler=HANDLER_NAME,
    )

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
    tracer = init_tracer(HANDLER_NAME, otlp_endpoint)
    setattr(context.user_data, "tracer", tracer)

    # Apply env-var defaults for cost config (overridden per-message at runtime)
    features_env = os.environ.get("CLASSIFICATION_FEATURES")
    if features_env:
        _cf.features = json.loads(features_env)
    normalizers_env = os.environ.get("CLASSIFICATION_PROPERTY_NORMALIZERS")
    if normalizers_env:
        _cf.PROPERTY_NORMALIZERS = json.loads(normalizers_env)
    costs_env = os.environ.get("CLASSIFICATION_NODE_COSTS")
    if costs_env:
        for k, v in json.loads(costs_env).items():
            setattr(_cf.NodeCost, k.upper(), float(v))


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
    settings = context.user_data.settings

    classification_params = {
        key: value
        for key, value in {
            **settings.model_dump(),
            **data["parameters"],
        }.items()
        if key in {"ged_timeout", "skeletonization_threshold", "simplification_epsilon", "comparison_method", "fgw_alpha"}
    }

    context.logger.info_with(
        f"Classification params: {classification_params}", handler=HANDLER_NAME
    )

    parent_ctx = extract_trace_context(event.headers)
    tracer = context.user_data.tracer

    with tracer.start_as_current_span(
        "classification.process", context=parent_ctx, kind=otel_trace.SpanKind.SERVER
    ) as span:
        span.set_attribute("image_id", image_id)

        orchestrator = ClassificationOrchestrator(
            neo4j_dsn=settings.neo4j_dsn,
            neo4j_user=settings.neo4j_user,
            neo4j_pass=settings.neo4j_pass,
            ged_timeout=classification_params["ged_timeout"],
            comparison_method=classification_params.get("comparison_method", "ged"),
            fgw_alpha=float(classification_params.get("fgw_alpha", 0.5)),
            tracer=tracer,
        )

        try:
            if not image_id:
                raise ValueError("image_id must be provided in the request body")

            msg_features = data["parameters"].get("features")
            msg_normalizers = data["parameters"].get("property_normalizers")
            msg_costs = data["parameters"].get("node_costs")

            with _cost_config_override(msg_features, msg_normalizers, msg_costs):
                comparison_results = orchestrator.classify_image(
                    image_id, context.user_data.concept_graphs
                )

            context.logger.info_with(
                f"Classification results: {len(comparison_results)} matches found",
                handler=HANDLER_NAME,
            )

            span.set_attribute("results_count", len(comparison_results))
            matching = [r for r in comparison_results if r.is_minor]
            if matching:
                span.set_attribute("predicted_concept", matching[0].concept_id)
                span.set_attribute("top_similarity", matching[0].similarity or 0)

            profiling["classification_time_ms"] = (time.time_ns() - start_time) / 1_000_000
            span.set_attribute("duration_ms", profiling["classification_time_ms"])

            context.user_data.kafka_producer.send(
                context.user_data.kafka_topic,
                value={
                    "status": "success",
                    "classification_results": [
                        result.__dict__ for result in comparison_results
                    ],
                    "image_id": image_id,
                    "image_path": data["parameters"]["image_path"],
                    "parameters": {**classification_params, **data["parameters"]},
                    "profiling": profiling,
                },
            )

        except Exception as e:
            span.record_exception(e)
            span.set_status(otel_trace.StatusCode.ERROR)
            context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
            logging.error(f"Error: {e}", exc_info=True, stack_info=True)

            context.user_data.kafka_producer.send(
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
