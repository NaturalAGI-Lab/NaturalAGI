"""Generic Nuclio Handler Template"""
import requests
import json
from pydantic_settings import BaseSettings
from graph_comparator import GraphComparator

HANDLER_NAME = "classification"

class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    next_nuclio: str = ""


def init_context(context):
    """Initializes Nuclio context

    Args:
        context: Nuclio context
    """

    context.logger.debug_with(
        f"Exporter initializing with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )
    settings = Settings()
    setattr(context.user_data, "next_nuclio", settings.next_nuclio)
    setattr(context.user_data, "graph_comparator", 
            GraphComparator(settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass))


def http_handler(context, event):
    """Handles HTTP requests"""
    try:
        # Parse the request body
        if isinstance(event.body, dict):
            data = event.body
        else:
            data = json.loads(event.body.decode('utf-8'))
        
        concept_id = data.get('concept_id')
        image_id = data.get('image_id')

        if not concept_id or not image_id:
            raise ValueError("Both concept_id and image_id must be provided in the request body")

        # Perform graph comparison
        similarity = context.user_data.graph_comparator.compare_graphs(concept_id, image_id)

        # Classify based on similarity
        classification = "Match" if similarity > 0.8 else "No Match"  # Adjust threshold as needed

        context.logger.info_with(f"Classification result: {classification}", handler=HANDLER_NAME)

        # Call next Nuclio functions if specified
        next_functions_str = context.user_data.next_nuclio
        if next_functions_str:
            next_nuclio = next_functions_str.split(";")
            context.logger.debug_with(f"Next functions: {next_nuclio}", handler=HANDLER_NAME)

            for func in next_nuclio:
                context.logger.info_with(f"Calling {func}", handler=HANDLER_NAME)
                requests.post(func, json={"image_id": image_id})

        # Responding to the HTTP request
        return context.Response(
            body=json.dumps({
                "classification": classification, 
                "similarity": similarity,
                "concept_id": concept_id,
                "image_id": image_id
            }),
            headers={},
            content_type="application/json",
            status_code=200,
        )

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        
        return context.Response(
            body=json.dumps({"error": str(e)}),
            headers={},
            content_type="application/json",
            status_code=500,
        )


def handler(context, event):
    """Nuclio main handler"""

    context.logger.info_with(f"Received request: {event.trigger.kind}", handler=HANDLER_NAME)
    context.logger.info_with(f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME)

    if event.trigger.kind == "http":
        return http_handler(context, event)
    else:
        context.logger.error_with("Unknown trigger. Only HTTP supported", handler=HANDLER_NAME)