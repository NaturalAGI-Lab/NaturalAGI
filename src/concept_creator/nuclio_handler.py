"""Nuclio Handler for Concept Creator"""

import requests
import traceback
import json
import os
import logging
import time
from typing import Dict, Any, List
from pydantic_settings import BaseSettings

from concept_creation_repository import ConceptCreationRepository
from energy_minimization_concept_service import EnergyMinimizationConceptService

HANDLER_NAME = "concept_creator"


class Settings(BaseSettings):
    """Settings for the concept creator service"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    next_nuclio: str = ""

def init_context(context):
    """
    Initialize the handler context with required services.
    """
    settings = Settings()

    # Initialize services
    context.energy_minimization_service = EnergyMinimizationConceptService(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    context.repository = ConceptCreationRepository(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    context.settings = settings

    return context


def handler(context, event):
    """
    Handle concept creation requests.
    """
    try:
        start_time = time.time()
        context.logger.info("Starting concept creation handler")

        # Parse the event body
        body = json.loads(event.body.decode("utf-8"))
        context.logger.info(f"Body: {body}")
        session_id = body.get("session_id")
        concept_id = body.get("concept_id")

        if not session_id:
            return context.Response(
                body=json.dumps({"error": "Missing session_id"}),
                status_code=400,
                content_type="application/json",
            )

        # Log input parameters
        context.logger.info(
            f"Creating concept for session {session_id}"
        )

        concept_id, concept_graph = (
            context.energy_minimization_service.create_concept_incrementally(
                session_id, concept_id
            )
        )

        # Create response with execution details
        execution_time = time.time() - start_time
        response = {
            "concept_id": concept_id,
            "session_id": session_id,
            "nodes_count": len(concept_graph.nodes()),
            "edges_count": len(concept_graph.edges()),
            "execution_time_seconds": execution_time,
        }

        context.logger.info(
            f"Concept creation completed in {execution_time:.2f}s. "
            f"Created concept {concept_id} with {len(concept_graph.nodes())} nodes and "
            f"{len(concept_graph.edges())} edges"
        )

        # Call next functions in the chain if specified
        next_functions_str = context.settings.next_nuclio
        if next_functions_str:
            next_nuclio = next_functions_str.split(";")
            for func in next_nuclio:
                context.logger.info(f"Calling next function: {func}")
                try:
                    requests.post(func, json={"concept_id": concept_id})
                except Exception as e:
                    context.logger.error(
                        f"Error calling next function {func}: {str(e)}"
                    )

        return context.Response(
            body=json.dumps(response), status_code=200, content_type="application/json"
        )

    except Exception as e:
        context.logger.error(f"Error creating concept: {str(e)}")
        context.logger.error(traceback.format_exc())

        return context.Response(
            body=json.dumps({"error": str(e), "traceback": traceback.format_exc()}),
            status_code=500,
            content_type="application/json",
        )


def create_success_response(context, data: Dict[str, Any]) -> Dict:
    """Create a success response."""
    return context.Response(
        body=json.dumps(data),
        headers={},
        content_type="application/json",
        status_code=200,
    )


def create_error_response(context, error_message: str) -> Dict:
    """Create an error response."""
    return context.Response(
        body=json.dumps({"error": error_message}),
        headers={},
        content_type="application/json",
        status_code=400,
    )
