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
from graph_intersection_concept_service import GraphIntersectionConceptService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("concept_creator")

HANDLER_NAME = "concept_creator"


class Settings(BaseSettings):
    """Settings for the concept creator service"""

    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
    next_nuclio: str = ""
    default_algorithm: str = (
        "graph_intersection"  # Can be 'energy_minimization' or 'graph_intersection'
    )


def init_context(context):
    """
    Initialize the handler context with required services.
    """
    settings = Settings()

    # Set up logger
    context.logger.setLevel(logging.INFO)

    # Initialize services
    context.energy_minimization_service = EnergyMinimizationConceptService(
        settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
    )
    context.graph_intersection_service = GraphIntersectionConceptService(
        settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
    )
    context.repository = ConceptCreationRepository(
        settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
    )
    context.settings = settings

    context.logger.info(
        f"Concept creator initialized with default algorithm: {settings.default_algorithm}"
    )

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
        session_id = body.get("session_id")
        concept_id = body.get("concept_id")
        algorithm = body.get("algorithm", context.settings.default_algorithm)

        if not session_id:
            return context.Response(
                body=json.dumps({"error": "Missing session_id"}),
                status_code=400,
                content_type="application/json",
            )

        # Log input parameters
        context.logger.info(
            f"Creating concept for session {session_id} using algorithm: {algorithm}"
        )

        # Create the concept based on the specified algorithm
        if algorithm == "energy_minimization":
            concept_id, concept_graph = (
                context.energy_minimization_service.create_concept_incrementally(
                    session_id, concept_id
                )
            )
        elif algorithm == "graph_intersection":
            concept_id, concept_graph = (
                context.graph_intersection_service.create_concept(
                    session_id, concept_id
                )
            )
        else:
            return context.Response(
                body=json.dumps({"error": f"Unknown algorithm: {algorithm}"}),
                status_code=400,
                content_type="application/json",
            )

        # Create response with execution details
        execution_time = time.time() - start_time
        response = {
            "concept_id": concept_id,
            "session_id": session_id,
            "algorithm": algorithm,
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
