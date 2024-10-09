"""Generic Nuclio Handler Template"""
import os
import uuid
from kafka import KafkaProducer
import json
import traceback
from pydantic_settings import BaseSettings

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

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: json.dumps(k).encode('utf-8') if k else None
    )
    setattr(context.user_data, "kafka_topic", settings.kafka_topic)
    setattr(context.user_data, "kafka_producer", producer)


def http_handler(context, event):
    """Handles HTTP requests"""
    try:
        # Parse the JSON input
        data = event.body
        
        # Extract operation and parameters
        operation = data.get('operation')
        parameters = data.get('parameters', {})
        session_id = str(uuid.uuid4())
        
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
                    image_path = os.path.join(dataset_path, image_file)
                    send_to_kafka(context, image_path, operation, concept_name, session_id)
            # Handle single file path
            elif os.path.isfile(dataset_path):
                send_to_kafka(context, dataset_path, operation, concept_name, session_id)
            else:
                raise ValueError(f"Invalid dataset_path: {dataset_path}")
            
            return context.Response(
                body="Images processed and sent to Kafka",
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

def send_to_kafka(context, image_path: str, operation: str, concept_name: str, session_id: str):
    kafka_message = {
        "operation": operation,
        "parameters": {
            "concept_name": concept_name,
            "image_path": image_path,
            "session_id": session_id,
            "image_id": str(uuid.uuid4())
        }
    }
    
    context.user_data.kafka_producer.send(
        context.user_data.kafka_topic,
        value=kafka_message
    )
    context.logger.info_with(f"Image path sent to Kafka: {image_path}", handler=HANDLER_NAME)


def handler(context, event):
    """Nuclio main handler"""

    context.logger.info_with(f"Received request: {event.trigger.kind}", handler=HANDLER_NAME)
    context.logger.info_with(f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME)

    if event.trigger.kind == "http":
        return http_handler(context, event)
    else:
        context.logger.error_with("Unknown trigger. Only HTTP supported", handler=HANDLER_NAME)