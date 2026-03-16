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

        experiment_id = parameters.get("mlflow_experiment_id")
        if experiment_id:
            context.user_data.tracer = init_tracer(HANDLER_NAME, experiment_id)
        tracer = context.user_data.tracer

        parent_ctx = extract_trace_context(event.headers)
        with tracer.start_as_current_span(
            "skeletonization.process", context=parent_ctx, kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("image_id", parameters.get("image_id", ""))
            span.set_attribute("operation", operation or "")
            if parameters.get("mlflow_run_id"):
                span.set_attribute("mlflow.run_id", parameters["mlflow_run_id"])

            context.logger.info_with(
                f"Received request: {event.trigger.kind}", handler=HANDLER_NAME
            )
            context.logger.info_with(f"Operation: {operation}", handler=HANDLER_NAME)
            context.logger.info_with(f"Parameters: {parameters}", handler=HANDLER_NAME)

            image = cv2.imread(parameters["image_path"], 0)

            image_width = image.shape[1]
            image_height = image.shape[0]
            span.set_attribute("image_width", image_width)
            span.set_attribute("image_height", image_height)

            parameters["image_width"] = image_width
            parameters["image_height"] = image_height

            settings = context.user_data.settings
            skeletonization_threshold = parameters.get(
                "skeletonization_threshold", settings.skeletonization_threshold
            )
            simplification_epsilon = parameters.get(
                "simplification_epsilon", settings.simplification_epsilon
            )
            graph, threshold = SkeletonGNGMapper(
                settings, skeletonization_threshold, simplification_epsilon
            ).process_image(image)
            data["parameters"]["skeletonization_threshold"] = threshold
            data["parameters"]["simplification_epsilon"] = simplification_epsilon
            span.set_attribute("final_threshold", threshold)

            json_net = GraphSerializer.serialize(graph)
            context.logger.info_with(f"Net: {json_net}", handler=HANDLER_NAME)

            context.logger.info_with("Processed request successfully", handler=HANDLER_NAME)
            data["skeleton"] = json_net

            if "profiling" not in data:
                data["profiling"] = {}
            data["profiling"]["skeletonization_time_ms"] = (
                time.time_ns() - start_time
            ) / 1_000_000
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
