"""Generic Nuclio Handler Template"""

import json
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from kafka import KafkaProducer
from neo4j import GraphDatabase
from pydantic_settings import BaseSettings
from opentelemetry import trace as otel_trace
from common.tracing import init_tracer, extract_trace_context
from classification_orchestrator import ClassificationOrchestrator
import classification_orchestrator as _orch
from graph_similarity import cost_functions as _cf
from repository.concept_repository import ConceptRepository
from repository.image_repository import ImageRepository
from band.band_repository import load_band_models, remove_image_features

HANDLER_NAME = "classification"

# Cross-process reload signal. The HTTP control worker and the Kafka classify worker
# are separate processes (one per trigger) that cannot share in-memory state, but they
# share the container filesystem. The control op touches this file; the Kafka worker
# reloads its cache when the file is newer than its last load. Overridable for tests.
RELOAD_SIGNAL_PATH = os.environ.get(
    "CONCEPT_RELOAD_SIGNAL_PATH", "/tmp/nuclio_concept_cache_reload"
)


def _reload_signal_mtime() -> float:
    try:
        return os.stat(RELOAD_SIGNAL_PATH).st_mtime
    except OSError:
        return 0.0


def _raise_reload_signal() -> None:
    Path(RELOAD_SIGNAL_PATH).touch()


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


def _annotate_range_widths(concept_graphs: dict) -> None:
    for graph in concept_graphs.values():
        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]
            widths: dict[str, float] = {}
            for key, val in node_data.items():
                if isinstance(val, dict) and "min" in val and "max" in val:
                    widths[key] = abs(float(val["max"]) - float(val["min"]))
            node_data["_range_widths"] = widths


@contextmanager
def _cost_config_override(features=None, costs=None, epsilon=None,
                         coverage_alpha=None, complexity_lambda=None,
                         range_gate=None, range_span=None,
                         insert_cost=None, eligibility_slack=None):
    orig_features = _cf.features
    orig_epsilon = _cf.DIAGNOSTIC_WEIGHT_EPSILON
    orig_gate, orig_span = _cf.RANGE_GATE_REL_WIDTH, _cf.RANGE_SOFTEN_SPAN
    orig_costs = {k: v for k, v in vars(_cf.NodeCost).items() if not k.startswith("_")}
    orig_cov = _orch.COVERAGE_ALPHA
    orig_lam = _orch.COMPLEXITY_PRIOR_LAMBDA
    orig_ins, orig_slack = _cf.CONCEPT_NODE_INSERT_COST, _orch.ELIGIBILITY_SLACK
    try:
        if insert_cost is not None:
            _cf.CONCEPT_NODE_INSERT_COST = float(insert_cost)
        if eligibility_slack is not None:
            _orch.ELIGIBILITY_SLACK = float(eligibility_slack)
        if features is not None:
            _cf.features = features
        if epsilon is not None:
            _cf.DIAGNOSTIC_WEIGHT_EPSILON = float(epsilon)
        if costs is not None:
            for k, v in costs.items():
                setattr(_cf.NodeCost, k.upper(), float(v))
        if coverage_alpha is not None:
            _orch.COVERAGE_ALPHA = float(coverage_alpha)
        if complexity_lambda is not None:
            _orch.COMPLEXITY_PRIOR_LAMBDA = float(complexity_lambda)
        if range_gate is not None:
            _cf.RANGE_GATE_REL_WIDTH = float(range_gate)
        if range_span is not None:
            _cf.RANGE_SOFTEN_SPAN = float(range_span)
        yield
    finally:
        _cf.features = orig_features
        _cf.DIAGNOSTIC_WEIGHT_EPSILON = orig_epsilon
        for k, v in orig_costs.items():
            setattr(_cf.NodeCost, k, v)
        _orch.COVERAGE_ALPHA = orig_cov
        _orch.COMPLEXITY_PRIOR_LAMBDA = orig_lam
        _cf.RANGE_GATE_REL_WIDTH, _cf.RANGE_SOFTEN_SPAN = orig_gate, orig_span
        _cf.CONCEPT_NODE_INSERT_COST, _orch.ELIGIBILITY_SLACK = orig_ins, orig_slack


def _message_overrides(parameters):
    """Per-message cost overrides; the same set for the traced and the untraced path."""
    return dict(
        features=parameters.get("features"),
        costs=parameters.get("node_costs"),
        epsilon=parameters.get("diagnostic_weight_epsilon"),
        coverage_alpha=parameters.get("coverage_alpha"),
        complexity_lambda=parameters.get("complexity_prior_lambda"),
        range_gate=parameters.get("range_gate_rel_width"),
        range_span=parameters.get("range_soften_span"),
        insert_cost=parameters.get("concept_node_insert_cost"),
        eligibility_slack=parameters.get("eligibility_slack"),
    )


def _load_concept_cache(context) -> int:
    """(Re)load concept graphs from Neo4j into the per-instance cache.

    Shared by init_context() and the HTTP reload_concepts control op so there is
    a single source of truth for what "the cache" contains. Each instance runs
    maxWorkers=1, so swapping the dict here cannot interleave with a classify.
    """
    concept_repo = ConceptRepository(context.user_data.neo4j_driver)
    concept_ids = concept_repo.get_all_concept_ids()
    concept_graphs = {
        cid: concept_repo.get_concept_graph(cid) for cid in concept_ids
    }
    _annotate_range_widths(concept_graphs)
    _cf.compute_feature_global_spans(concept_graphs)
    setattr(context.user_data, "concept_graphs", concept_graphs)
    setattr(context.user_data, "concept_reload_mtime", _reload_signal_mtime())
    # Band models (graph-level band concepts) and the structural graphs that only explain
    # their leaves. Both are empty unless a band model has been trained; band_mode defaults
    # to "off", in which case neither is ever read.
    try:
        band_models = load_band_models(context.user_data.neo4j_driver)
        explainer_graphs = {
            cid: concept_repo.get_concept_graph(cid)
            for cid in concept_repo.get_explainer_concept_ids()
        }
        _annotate_range_widths(explainer_graphs)
    except Exception as e:  # noqa: BLE001
        context.logger.error_with(f"Band models not loaded: {e}", handler=HANDLER_NAME)
        band_models, explainer_graphs = {}, {}
    setattr(context.user_data, "band_models", band_models)
    setattr(context.user_data, "explainer_graphs", explainer_graphs)
    context.logger.info_with(
        f"Loaded + annotated {len(concept_graphs)} concept graphs",
        handler=HANDLER_NAME,
    )
    return len(concept_graphs)


def _maybe_reload_concepts(context) -> None:
    """Hot-reload the concept cache if another worker raised the reload signal.

    The HTTP control op and this Kafka worker are separate processes, so the op
    cannot mutate this worker's cache directly — it touches a shared signal file
    instead. We reload only when that file is newer than our last load, so the
    cost on the classify path is a single os.stat per message.
    """
    if _reload_signal_mtime() > getattr(context.user_data, "concept_reload_mtime", 0.0):
        context.logger.info_with(
            "Concept reload signal detected; reloading concept cache",
            handler=HANDLER_NAME,
        )
        _load_concept_cache(context)


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

    driver = GraphDatabase.driver(
        settings.neo4j_dsn, auth=(settings.neo4j_user, settings.neo4j_pass)
    )
    setattr(context.user_data, "neo4j_driver", driver)

    _load_concept_cache(context)

    tracer = init_tracer(HANDLER_NAME)
    setattr(context.user_data, "tracer", tracer)

    # Apply env-var defaults for cost config (overridden per-message at runtime)
    features_env = os.environ.get("CLASSIFICATION_FEATURES")
    if features_env:
        _cf.features = json.loads(features_env)
    costs_env = os.environ.get("CLASSIFICATION_NODE_COSTS")
    if costs_env:
        for k, v in json.loads(costs_env).items():
            setattr(_cf.NodeCost, k.upper(), float(v))
    epsilon_env = os.environ.get("CLASSIFICATION_DIAGNOSTIC_WEIGHT_EPSILON")
    if epsilon_env:
        _cf.DIAGNOSTIC_WEIGHT_EPSILON = float(epsilon_env)
    gate_env = os.environ.get("CLASSIFICATION_RANGE_GATE_REL_WIDTH")
    if gate_env:
        _cf.RANGE_GATE_REL_WIDTH = float(gate_env)
    span_env = os.environ.get("CLASSIFICATION_RANGE_SOFTEN_SPAN")
    if span_env:
        _cf.RANGE_SOFTEN_SPAN = float(span_env)


def kafka_handler(context, event):
    """Handles HTTP requests"""
    start_time = time.time_ns()
    if isinstance(event.body, dict):
        data = event.body
    else:
        data = json.loads(event.body.decode("utf-8"))

    if data["operation"] != "classify":
        return

    _maybe_reload_concepts(context)

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
        if key in {"ged_timeout", "skeletonization_threshold", "simplification_epsilon", "comparison_method", "fgw_alpha", "preprocess_fallback", "calibration", "band_mode", "band_model", "band_topk"}
    }

    context.logger.info_with(
        f"Classification params: {classification_params}", handler=HANDLER_NAME
    )

    tracing_disabled = bool(data["parameters"].get("disable_tracing"))

    if tracing_disabled:
        _classify_no_trace(context, data, image_id, classification_params,
                           profiling, delete_image_nodes, start_time)
    else:
        _classify_with_trace(context, event, data, image_id, classification_params,
                             profiling, delete_image_nodes, start_time)


def _cleanup_image_features(context, data, image_id) -> None:
    """The per-image :GraphFeatures node exists only when the request asked for a direction map."""
    params = data.get("parameters", {})
    wanted = params.get("direction_map") or params.get("band_mode", "off") != "off"
    if wanted and params.get("delete_image_nodes", True) and not params.get("keep_graph_features"):
        try:
            remove_image_features(context.user_data.neo4j_driver, image_id)
        except Exception as e:  # noqa: BLE001
            context.logger.error_with(f"GraphFeatures cleanup failed: {e}", handler=HANDLER_NAME)


def _band_kwargs(context, classification_params) -> dict:
    """Orchestrator kwargs for band mode. `off` (default) passes nothing model-related."""
    band_mode = str(classification_params.get("band_mode", "off"))
    if band_mode == "off":
        return {"band_mode": "off"}
    name = classification_params.get("band_model")
    models = getattr(context.user_data, "band_models", {}) or {}
    # A missing model is reported by the orchestrator inside the classify try-block, so the
    # message still reaches the DLQ and the image nodes are still cleaned up.
    return {
        "band_mode": band_mode,
        "band_model": models.get(name),
        "band_model_name": name,
        "band_topk": int(classification_params.get("band_topk", 3)),
        "explainer_graphs": getattr(context.user_data, "explainer_graphs", {}) or {},
    }


def _classify_no_trace(context, data, image_id, classification_params,
                       profiling, delete_image_nodes, start_time):
    orchestrator = ClassificationOrchestrator(
        driver=context.user_data.neo4j_driver,
        ged_timeout=classification_params["ged_timeout"],
        comparison_method=classification_params.get("comparison_method", "ged"),
        fgw_alpha=float(classification_params.get("fgw_alpha", 0.5)),
        preprocess_fallback=bool(classification_params.get("preprocess_fallback", False)),
        calibration=str(classification_params.get("calibration", "off")),
        **_band_kwargs(context, classification_params),
        tracer=None,
    )
    try:
        if not image_id:
            raise ValueError("image_id must be provided in the request body")

        with _cost_config_override(**_message_overrides(data["parameters"])):
            comparison_results = orchestrator.classify_image(
                image_id, context.user_data.concept_graphs
            )

        context.logger.info_with(
            f"Classification results: {len(comparison_results)} matches found",
            handler=HANDLER_NAME,
        )

        profiling["classification_time_ms"] = (time.time_ns() - start_time) / 1_000_000
        context.user_data.kafka_producer.send(
            context.user_data.kafka_topic,
            value={
                "status": "success",
                "classification_results": [r.__dict__ for r in comparison_results],
                "image_id": image_id,
                "image_path": data["parameters"]["image_path"],
                "parameters": {**classification_params, **data["parameters"]},
                "profiling": profiling,
            },
        )

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        logging.error(f"Error: {e}", exc_info=True, stack_info=True)
        context.user_data.kafka_producer.send(
            context.user_data.dlq_topic,
            value={"error": str(e), "source": HANDLER_NAME, "value": data},
        )

    finally:
        if delete_image_nodes:
            image_repository = ImageRepository(context.user_data.neo4j_driver)
            image_repository.remove_image_nodes(image_id)
        _cleanup_image_features(context, data, image_id)


def _classify_with_trace(context, event, data, image_id, classification_params,
                         profiling, delete_image_nodes, start_time):
    experiment_id = data["parameters"].get("mlflow_experiment_id")
    if experiment_id:
        context.user_data.tracer = init_tracer(HANDLER_NAME, experiment_id)

    parent_ctx = extract_trace_context(event.headers)
    tracer = context.user_data.tracer

    with tracer.start_as_current_span(
        "classification.process", context=parent_ctx, kind=otel_trace.SpanKind.SERVER
    ) as span:
        span.set_attribute("image_id", image_id)
        if data["parameters"].get("mlflow_run_id"):
            span.set_attribute("mlflow.run_id", data["parameters"]["mlflow_run_id"])

        orchestrator = ClassificationOrchestrator(
            driver=context.user_data.neo4j_driver,
            ged_timeout=classification_params["ged_timeout"],
            comparison_method=classification_params.get("comparison_method", "ged"),
            fgw_alpha=float(classification_params.get("fgw_alpha", 0.5)),
            preprocess_fallback=bool(classification_params.get("preprocess_fallback", False)),
            calibration=str(classification_params.get("calibration", "off")),
            **_band_kwargs(context, classification_params),
            tracer=tracer,
        )

        try:
            if not image_id:
                raise ValueError("image_id must be provided in the request body")

            with _cost_config_override(**_message_overrides(data["parameters"])):
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
                image_repository = ImageRepository(context.user_data.neo4j_driver)
                image_repository.remove_image_nodes(image_id)
            _cleanup_image_features(context, data, image_id)


def http_handler(context, event):
    """Handles HTTP control requests (cache invalidation, health ping).

    `reload_concepts` runs on the HTTP-trigger worker, a SEPARATE process from the
    Kafka-trigger worker that actually classifies — so reloading this worker's cache
    alone is invisible to the classify path. We therefore raise a shared filesystem
    signal that the Kafka worker checks per message and reloads on (see
    `_maybe_reload_concepts`). Invoked per-instance via `nuctl invoke` (the
    `reload_concepts` Makefile target fans out to every instance).
    """
    try:
        body = event.body if isinstance(event.body, dict) else json.loads(event.body or b"{}")
    except (ValueError, TypeError):
        body = {}

    operation = body.get("operation")
    if operation == "band_status":
        models = getattr(context.user_data, "band_models", {}) or {}
        return json.dumps({
            "status": "ok",
            "band_models": {k: {"concepts": len(m.band_ids), "dm_version": m.dm_version} for k, m in models.items()},
            "explainer_graphs": len(getattr(context.user_data, "explainer_graphs", {}) or {}),
            "structural_concepts": len(getattr(context.user_data, "concept_graphs", {}) or {}),
        })
    if operation == "reload_concepts":
        _raise_reload_signal()
        count = _load_concept_cache(context)
        return json.dumps(
            {"status": "reloaded", "concept_count": count, "signal_raised": True}
        )

    return json.dumps({"status": "ok"})


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
    return http_handler(context, event)
