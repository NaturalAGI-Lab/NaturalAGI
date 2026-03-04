"""Generic Nuclio Handler Template"""
import os
import uuid
from kafka import KafkaProducer
import json
import traceback
from pydantic_settings import BaseSettings
from common.tracing import init_tracer, inject_trace_headers

HANDLER_NAME = "connector"

class Settings(BaseSettings):
    """Settings"""

    kafka_topic: str
    kafka_bootstrap_servers: str
    kafka_group_id: str = "connector"


def init_context(context):
    """Initializes Nuclio context

    Args:
        context: Nuclio context
    """
    settings = Settings()
    context.logger.debug_with(
        f"Exporter initializing with:\n{settings.model_dump()}", handler=HANDLER_NAME
    )

    setattr(context.user_data, "kafka_topic", settings.kafka_topic)
    setattr(context.user_data, "kafka_bootstrap_servers", settings.kafka_bootstrap_servers)

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    setattr(context.user_data, "kafka_producer", producer)

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
    tracer = init_tracer(HANDLER_NAME, otlp_endpoint)
    setattr(context.user_data, "tracer", tracer)


def http_handler(context, event):
    """Handles HTTP requests"""
    try:
        # Parse the JSON input
        data = event.body
        if isinstance(data, bytes):
            data = json.loads(data)
        context.logger.info_with(f"Received request: {data}", handler=HANDLER_NAME)

        # Extract operation and parameters
        operation = data.get('operation')
        parameters = data.get('parameters', {})
        session_id = parameters.get('session_id', str(uuid.uuid4()))

        parameters["session_id"] = session_id

        context.logger.info_with(f"Received request: {event.trigger.kind}", handler=HANDLER_NAME)
        context.logger.info_with(f"Operation: {operation}", handler=HANDLER_NAME)
        context.logger.info_with(f"Parameters: {parameters}", handler=HANDLER_NAME)
        context.logger.info_with(f"Session ID: {session_id}", handler=HANDLER_NAME)

        if operation == 'train':
            dataset_path = parameters.get('dataset_path')
            concept_name = parameters.get('concept_name')

            if not dataset_path or not concept_name:
                raise ValueError("Both dataset_path and concept_name are required for training")

            # Handle folder path
            if os.path.isdir(dataset_path):
                image_files = [f for f in os.listdir(dataset_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                for image_file in image_files:
                    parameters["image_path"] = os.path.join(dataset_path, image_file)
                    parameters["image_id"] = str(uuid.uuid4())
                    send_to_kafka(context, operation, parameters)
            # Handle single file path
            elif os.path.isfile(dataset_path):
                parameters["image_path"] = dataset_path
                parameters["image_id"] = str(uuid.uuid4())
                send_to_kafka(context, operation, parameters)
            else:
                raise ValueError(f"Invalid dataset_path: {dataset_path}")

            context.user_data.kafka_producer.flush()
            return context.Response(
                body="Images processed and sent to Kafka",
                headers={},
                content_type="text/plain",
                status_code=200,
            )
        elif operation == 'classify':
            image_path = parameters.get('image_path')

            if not image_path:
                raise ValueError("image_path is required for classification")

            if not os.path.isfile(image_path):
                raise ValueError(f"Invalid image_path: {image_path}")

            parameters["image_id"] = parameters.get("image_id", str(uuid.uuid4()))

            with context.user_data.tracer.start_as_current_span("connector.classify") as span:
                span.set_attribute("image_id", parameters["image_id"])
                span.set_attribute("image_path", image_path)
                span.set_attribute("session_id", parameters.get("session_id", ""))
                send_to_kafka(context, operation, parameters)

            return context.Response(
                body="Image sent for classification",
                headers={},
                content_type="text/plain",
                status_code=200,
            )
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        traceback.print_exc()

        return context.Response(
            body=f"Error: {e}",
            headers={},
            content_type="text/plain",
            status_code=500,
        )

def send_to_kafka(context, operation: str, parameters: dict):
    kafka_message = {
        "operation": operation,
        "parameters": parameters
    }
    headers = inject_trace_headers()
    context.user_data.kafka_producer.send(
        context.user_data.kafka_topic,
        value=kafka_message,
        headers=headers,
    )
    context.logger.info_with(f"Image path sent to Kafka: {parameters['image_path']}", handler=HANDLER_NAME)

def handler(context, event):
    """Nuclio main handler"""

    context.logger.info_with(f"Received request: {event.trigger.kind}", handler=HANDLER_NAME)
    context.logger.info_with(f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME)

    if event.trigger.kind == "http":
        return http_handler(context, event)
    else:
        context.logger.error_with("Unknown trigger. Only HTTP supported", handler=HANDLER_NAME)
