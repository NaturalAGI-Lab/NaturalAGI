from __future__ import annotations

import logging
from neo4j import ManagedTransaction
import numpy as np

from logic.helpers import calculate_half_plane_and_quadrant
from model.angle_point import AnglePoint
from model.vector_details import VectorDetails


def get_attribute(obj, attr):
    if isinstance(obj, dict):
        return obj.get(attr, None)  # None is default if key doesn't exist
    else:
        return getattr(obj, attr, None)  # None is default if attribute doesn't exist


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
    print(f"X:{get_attribute(angle_point, 'x')}")
    starting_x: float = get_attribute(angle_point, 'x')
    starting_y: float = get_attribute(angle_point, 'y')
    ending_x: float | None = None
    ending_y: float | None = None

    if vector.x1 == starting_x and vector.y1 == starting_y:
        ending_x = vector.x2
        ending_y = vector.y2
    else:
        ending_x = vector.x1
        ending_y = vector.y1

    print(f"Subtracting {(ending_x, ending_y), (starting_x, starting_y)}")

    x_vect: float
    y_vect: float
    x_vect, y_vect = np.subtract((ending_x, ending_y), (starting_x, starting_y))

    print(f"Vector value: {x_vect, y_vect}")

    query = """
        MATCH (vector:Vector)
        WHERE vector.vector_id = $vector_id
        WITH vector
        CREATE (vValue:VectorValue {x: $x_vect, y: $y_vect})
        WITH vector, vValue
        CREATE (vector)-[:HAS_VECTOR_VALUE]->(vValue)
    """
    tx.run(query, vector_id=vector.id, x_vect=x_vect, y_vect=y_vect)
    print("Vector value is created for the line")

    horizontal_plane, vertical_plane, quadrant = calculate_half_plane_and_quadrant(
        x_vect, y_vect
    )
    print(
        f"Half planes and quadrants: {horizontal_plane, vertical_plane, quadrant}"
    )
    query = """
        MATCH (vector:Vector)
        WHERE vector.vector_id = $vector_id
        WITH vector
        CREATE (vertical:VerticalVectorHalfPlane {vertical_plane: $vertical_plane})
        CREATE (horizontal:HorizontalVectorHalfPlane {horizontal_plane: $horizontal_plane})
        CREATE (vector)-[:HAS_VERTICAL_VECTOR_HALF_PLANE]->(vertical)
        CREATE (vector)-[:HAS_HORIZONTAL_VECTOR_HALF_PLANE]->(horizontal)
    """
    result = tx.run(
        query,
        vector_id=vector.id,
        horizontal_plane=horizontal_plane,
        vertical_plane=vertical_plane,
    )

    query = """
        MATCH (vector:Vector)
        WHERE vector.vector_id = $vector_id
        WITH vector
        CREATE (quadrant:Quadrant {quadrant: $quadrant})
        CREATE (vector)-[:HAS_QUADRANT]->(quadrant)
    """
    result = tx.run(query, vector_id=vector.id, quadrant=quadrant)
    print(f"Half planes and quadrants are created for the vector: {vector.id} quadrant:{quadrant} ")
    return result


# def _create_relative_characteristics(tx, image_id):
#     logging.debug("Running _create_relative_characteristics transaction")
#     query = """
#             MATCH (coord:Coordinates)--(:Location)--(vector:Vector {image_id: $image_id})-[:HAS_ANGLE_POINT]->(ap1:AnglePoint)--(apLoc1:AnglePointCoordinates),
#                 (vector)-[:HAS_ANGLE_POINT]->(ap2:AnglePoint)--(apLoc2:AnglePointCoordinates),
#                 (angle:Angle)--(:Orientation)--(vector)
#             WITH vector, apLoc1, apLoc2
#             MERGE (vCoordinates:Coordinates {x1: apLoc1.x, y1: apLoc1.y, x2: apLoc2.x, y2: apLoc2.y})
#             MERGE (v)-[:HAS_COORDINATES]->(vCoordinates)
#             WITH v, vCoordinates, sqrt((vCoordinates.x2 - vCoordinates.x1) * (vCoordinates.x2 - vCoordinates.x1) + (vCoordinates.y2 - vCoordinates.y1) * (vCoordinates.y2 - vCoordinates.y1)) AS magnitude
#             MERGE (vectorMagnitude:VectorMagnitude {value: magnitude})
#             MERGE (vectorMagnitude)<-[:HAS_MAGNITUDE]-(v)
#         """
#     logging.debug(f"Running query: {query}")
#     tx.run(query, image_id=image_id)
