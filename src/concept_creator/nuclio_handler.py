"""Nuclio Handler for Concept Creator"""

import requests
import traceback
import json
import time
from typing import Dict, Any
from pydantic_settings import BaseSettings

from src.concept_creation_repository import ConceptCreationRepository
from src.critical_point_concept_service import CriticalPointConceptService
from src.band_concepts.band_concept_service import BandConceptService
from src.band_concepts.band_repository import BandRepository

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

    context.critical_point_service = CriticalPointConceptService(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )

    context.repository = ConceptCreationRepository(
        settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass
    )
    context.settings = settings
    context.band_service = BandConceptService(
        BandRepository(settings.neo4j_dsn, settings.neo4j_user, settings.neo4j_pass)
    )

    return context


def _build_band_model(context, body: Dict[str, Any], start_time: float):
    """operation == "build_band_model": graph-level band concepts, independent of the fold."""
    if not body.get("model_id") or not body.get("forms"):
        return context.Response(
            body=json.dumps({"error": "build_band_model needs model_id and forms"}),
            status_code=400,
            content_type="application/json",
        )
    result = context.band_service.build_band_model(
        body["model_id"],
        body["forms"],
        merge_similar=bool(body.get("merge_similar", True)),
        q=float(body.get("q", 10.0)),
        root_scope=str(body.get("root_scope", "form")),
        block_weights=body.get("block_weights"),
        alpha=float(body.get("alpha", 5.0)),
        leaf_weight=float(body.get("leaf_weight", 0.7)),
        stage2_lambda=float(body.get("stage2_lambda", 0.0)),
        stage2_topk=int(body.get("stage2_topk", 5)),
        stage2_beta=float(body.get("stage2_beta", 0.3)),
    )
    result["execution_time_seconds"] = time.time() - start_time
    return context.Response(body=json.dumps(result), status_code=200, content_type="application/json")


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
        # Requests without `operation` are the structural fold below, unchanged.
        if body.get("operation") == "build_band_model":
            return _build_band_model(context, body, start_time)
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

        concept_result = (
            context.critical_point_service.create_concept_incrementally(
                session_id, concept_id
            )
        )
        concept_graph = concept_result.concept_graph

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
