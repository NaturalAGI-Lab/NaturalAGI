"""Generic Nuclio Handler Template"""

import dataclasses
import json
import time
import cv2
from kafka import KafkaProducer
import traceback
from common.model.dlq import DLQModel
from common.tracing import init_tracer, inject_trace_headers, extract_trace_context, SpanKind
from settings import Settings
from skeleton_gng_mapper import SkeletonGNGMapper
from dense_features import dense_representation
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

    setattr(context.user_data, "settings", settings)
    setattr(context.user_data, "kafka_topic", settings.kafka_topic)
    setattr(context.user_data, "dlq_topic", settings.dlq_topic)

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    setattr(context.user_data, "kafka_producer", producer)

    tracer = init_tracer(HANDLER_NAME)
    setattr(context.user_data, "tracer", tracer)


def kafka_handler(context, event):
    """Handles Kafka messages"""

    data = json.loads(event.body)

    try:
        start_time = time.time_ns()
        context.logger.info_with(f"Received request: {data}", handler=HANDLER_NAME)

        operation = data.get("operation")
        parameters = data.get("parameters", {})

        tracing_disabled = bool(parameters.get("disable_tracing"))

        if not tracing_disabled:
            experiment_id = parameters.get("mlflow_experiment_id")
            if experiment_id:
                context.user_data.tracer = init_tracer(HANDLER_NAME, experiment_id)

        context.logger.info_with(
            f"Received request: {event.trigger.kind}", handler=HANDLER_NAME
        )
        context.logger.info_with(f"Operation: {operation}", handler=HANDLER_NAME)
        context.logger.info_with(f"Parameters: {parameters}", handler=HANDLER_NAME)

        image = cv2.imread(parameters["image_path"], 0)

        image_width = image.shape[1]
        image_height = image.shape[0]

        parameters["image_width"] = image_width
        parameters["image_height"] = image_height

        settings = context.user_data.settings
        skeletonization_threshold = parameters.get(
            "skeletonization_threshold", settings.skeletonization_threshold
        )
        simplification_epsilon = parameters.get(
            "simplification_epsilon", settings.simplification_epsilon
        )
        mapper = SkeletonGNGMapper(
            settings,
            skeletonization_threshold,
            simplification_epsilon,
            thick_stroke_threshold=int(parameters.get("thick_stroke_threshold", 0) or 0),
            thick_stroke_px=float(parameters.get("thick_stroke_px", 8.0)),
            bridge_protect_stems=bool(parameters.get("bridge_protect_stems", False)),
            bridge_components=bool(parameters.get("bridge_components", False)),
        )
        graph, threshold = mapper.process_image(image)
        # Shape read off the dense centre line (orientation block + shape-context points); opt-in.
        want_dense = bool(parameters.get("dense_features", False))
        if want_dense:
            dense = dense_representation(mapper.last_skeleton, deslant=bool(parameters.get("deslant", False)), normalisation=str(parameters.get("normalisation", "bbox")), moment_range=float(parameters.get("moment_range", 2.0)))
            if dense is not None:
                data["dense"] = dense
        data["parameters"]["skeletonization_threshold"] = threshold
        data["parameters"]["simplification_epsilon"] = simplification_epsilon

        json_net = GraphSerializer.serialize(graph)
        context.logger.info_with(f"Net: {json_net}", handler=HANDLER_NAME)

        # Committee of skeletons: extra skeletons from other binarisations travel with the
        # message as `skeleton_alts`; only the direction map reads them (classification averages
        # the letter scores over all maps). `committee_threshold` = int or list; 0/absent = off.
        committee = parameters.get("committee_threshold", 0) or 0
        committee = [int(t) for t in (committee if isinstance(committee, list) else [committee]) if int(t) > 0]
        if committee:
            alts, dense_alts = [], []
            for thr in committee:
                try:
                    alt_mapper = SkeletonGNGMapper(
                        settings,
                        thr,
                        simplification_epsilon,
                        thick_stroke_threshold=int(parameters.get("thick_stroke_threshold", 0) or 0),
                        thick_stroke_px=float(parameters.get("thick_stroke_px", 8.0)),
                        bridge_protect_stems=bool(parameters.get("bridge_protect_stems", False)),
                        bridge_components=bool(parameters.get("bridge_components", False)),
                    )
                    alt_graph, _ = alt_mapper.process_image(image)
                    if want_dense:
                        alt_dense = dense_representation(alt_mapper.last_skeleton, deslant=bool(parameters.get("deslant", False)), normalisation=str(parameters.get("normalisation", "bbox")), moment_range=float(parameters.get("moment_range", 2.0)))
                        dense_alts.append(alt_dense["orient"] if alt_dense else None)
                    alts.append(GraphSerializer.serialize(alt_graph))
                except Exception as e:  # noqa: BLE001
                    context.logger.warn_with(f"Committee skeleton at {thr} failed: {e}", handler=HANDLER_NAME)
            if alts:
                data["skeleton_alts"] = alts
                if want_dense and len(dense_alts) == len(alts):
                    data["dense_alts"] = dense_alts

        context.logger.info_with("Processed request successfully", handler=HANDLER_NAME)
        data["skeleton"] = json_net

        if "profiling" not in data:
            data["profiling"] = {}
        data["profiling"]["skeletonization_time_ms"] = (
            time.time_ns() - start_time
        ) / 1_000_000

        if tracing_disabled:
            context.user_data.kafka_producer.send(
                context.user_data.kafka_topic, value=data, headers=[]
            )
        else:
            tracer = context.user_data.tracer
            parent_ctx = extract_trace_context(event.headers)
            with tracer.start_as_current_span(
                "skeletonization.process", context=parent_ctx, kind=SpanKind.SERVER
            ) as span:
                span.set_attribute("image_id", parameters.get("image_id", ""))
                span.set_attribute("operation", operation or "")
                if parameters.get("mlflow_run_id"):
                    span.set_attribute("mlflow.run_id", parameters["mlflow_run_id"])
                span.set_attribute("image_width", image_width)
                span.set_attribute("image_height", image_height)
                span.set_attribute("final_threshold", threshold)
                span.set_attribute(
                    "duration_ms", data["profiling"]["skeletonization_time_ms"]
                )

                headers = inject_trace_headers()
                context.user_data.kafka_producer.send(
                    context.user_data.kafka_topic, value=data, headers=headers
                )

    except Exception as e:
        context.logger.warn_with(f"Error: {e}", handler=HANDLER_NAME)
        traceback.print_exc()

        dlq_model = DLQModel(
            source=HANDLER_NAME,
            error={"error": str(e), "traceback": traceback.format_exc()},
            value=data,
        )
        context.user_data.kafka_producer.send(
            context.user_data.dlq_topic, value=dataclasses.asdict(dlq_model)
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
