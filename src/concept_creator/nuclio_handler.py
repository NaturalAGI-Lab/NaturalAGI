"""Generic Nuclio Handler Template"""

import requests
import traceback
from pydantic_settings import BaseSettings
import json

from concept_creation_repository import ConceptCreationRepository

HANDLER_NAME = "concept_creator"


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
    setattr(context.user_data, "next_nuclio", Settings().next_nuclio)
    setattr(
        context.user_data,
        "concept_creation_repository",
        ConceptCreationRepository(
            Settings().neo4j_dsn, Settings().neo4j_user, Settings().neo4j_pass
        ),
    )

    # Initialize and set context variables
    # Example: setattr(context.user_data, "example_variable", value)


def http_handler(context, event):
    """Handles HTTP requests"""
    try:

        repo = context.user_data.concept_creation_repository
        concept_id = repo.create_concept()
        repo.close()

        context.logger.info_with(
            f"Processed request successfully, concept_id: {concept_id}", handler=HANDLER_NAME
        )

        next_functions_str = context.user_data.next_nuclio

        if next_functions_str:
            next_nuclio = next_functions_str.split(";")
            context.logger.debug_with(
                f"Next functions: {next_nuclio}", handler=HANDLER_NAME
            )

            for func in next_nuclio:
                context.logger.info_with(f"Calling {func}", handler=HANDLER_NAME)
                requests.post(func, json={"concept_id": concept_id})

        # Responding to the HTTP request
        return context.Response(
            body=json.dumps({"concept_id": concept_id}),
            headers={},
            content_type="application/json",
            status_code=200,
        )

    except Exception as e:
        context.logger.error_with(f"Error: {e}", handler=HANDLER_NAME)
        traceback.print_exc()

        return context.Response(
            body=f"Error: {e}",
            headers={},
            content_type="text/plain",
            status_code=500,
        )


def handler(context, event):
    """Nuclio main handler"""

    context.logger.info_with(
        f"Received request: {event.trigger.kind}", handler=HANDLER_NAME
    )
    context.logger.info_with(
        f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME
    )

    if event.trigger.kind == "http":
        http_handler(context, event)
    else:
        context.logger.error_with(
            "Unknown trigger. Only HTTP supported", handler=HANDLER_NAME
        )