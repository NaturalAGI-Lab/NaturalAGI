from __future__ import annotations

import logging
from neo4j import ManagedTransaction
import numpy as np

from logic.helpers import calculate_half_plane_and_quadrant
from model.angle_point import AnglePoint
from model.vector_details import VectorDetails


# TODO - Add type hints, refactor to the smaller functions
def calculate_and_set_relative_params(
    tx: ManagedTransaction,
    vector: VectorDetails,
    angle_point: AnglePoint,
) -> None:
    """
    Calculates and sets the relative parameters for a given image.

    Args:
        tx (ManagedTransaction): The managed transaction object.
        image_id (str): The ID of the image.
    Returns:
        None
    """
    starting_x: float = angle_point.x
    starting_y: float = angle_point.y
    ending_x: float | None = None
    ending_y: float | None = None

    if vector.x1 == starting_x and vector.y1 == starting_y:
        ending_x = vector.x2
        ending_y = vector.y2
    else:
        ending_x = vector.x1
        ending_y = vector.y1

    logging.debug(f"Subtracting {(ending_x, ending_y), (starting_x, starting_y)}")

    x_vect: float
    y_vect: float
    x_vect, y_vect = np.subtract((ending_x, ending_y), (starting_x, starting_y))

    logging.debug(f"Vector value: {x_vect, y_vect}")

    query = """
        MATCH (vector:Vector)
        WHERE vector.vector_id = $vector_id
        WITH vector
        MERGE (vValue:VectorValue {x: $x_vect, y: $y_vect})
        MERGE (vector)-[:HAS_VECTOR_VALUE]->(vValue)
    """
    result = tx.run(query, vector_id=vector.uuid, x_vect=x_vect, y_vect=y_vect)
    logging.debug("Vector value is created for the line")

    horizontal_plane, vertical_plane, quadrant = calculate_half_plane_and_quadrant(
        x_vect, y_vect
    )
    logging.debug(
        f"Half planes and quadrants: {horizontal_plane, vertical_plane, quadrant}"
    )
    query = """
        MATCH (vector:Vector)
        WHERE vector.vector_id = $vector_id
        WITH vector
        MERGE (vertical:VerticalVectorHalfPlane {vertical_plane: $vertical_plane})
        MERGE (horizontal:HorizontalVectorHalfPlane {horizontal_plane: $horizontal_plane})
        MERGE (vector)-[:HAS_VERTICAL_VECTOR_HALF_PLANE]->(vertical)
        MERGE (vector)-[:HAS_HORIZONTAL_VECTOR_HALF_PLANE]->(horizontal)
    """
    result = tx.run(
        query,
        vector_id=vector.uuid,
        horizontal_plane=horizontal_plane,
        vertical_plane=vertical_plane,
    )

    query = """
        MATCH (vector:Vector)
        WHERE vector.vector_id = $vector_id
        WITH vector
        MERGE (quadrant:Quadrant {quadrant: $quadrant})
        MERGE (vector)-[:HAS_QUADRANT]->(quadrant)
    """
    result = tx.run(query, vector_id=vector.uuid, quadrant=quadrant)
    logging.debug("Half planes and quadrants are created for the line ")
    return result
