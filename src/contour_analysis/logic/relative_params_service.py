from __future__ import annotations

import numpy as np
from neo4j import ManagedTransaction

from logic.helpers import calculate_half_plane_and_quadrant
from model.angle_point import Point
from model.vector_details import VectorDetails


def get_attribute(obj, attr):
    if isinstance(obj, dict):
        return obj.get(attr, None)  # None is default if key doesn't exist
    else:
        return getattr(obj, attr, None)  # None is default if attribute doesn't exist


def calculate_and_set_relative_params(
    tx: ManagedTransaction,
    vector: VectorDetails,
    angle_point: Point,
    image_id: str,
    session_id: str,
) -> None:
    """
    Calculates and sets the relative parameters for a given image.

    Args:
        tx (ManagedTransaction): The managed transaction object.
        vector (VectorDetails): The vector details object.
        angle_point (AnglePoint): The angle point object.
    Returns:
        None
    """
    print(f"X:{get_attribute(angle_point, 'x')}")
    starting_x: float = get_attribute(angle_point, "x")
    starting_y: float = get_attribute(angle_point, "y")

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
        MATCH (vector:Vector {vector_id: $vector_id})
        MERGE (vValue:VectorValue:Feature {x: $x_vect, y: $y_vect, session_id: $session_id})
        ON CREATE SET vValue.samples = [$image_id]
        ON MATCH SET vValue.samples = CASE WHEN $image_id IN vValue.samples THEN vValue.samples ELSE vValue.samples + $image_id END
        WITH vector, vValue
        MERGE (vector)-[:HAS_VECTOR_VALUE]->(vValue)
    """
    tx.run(
        query,
        vector_id=vector.id,
        x_vect=x_vect,
        y_vect=y_vect,
        image_id=image_id,
        session_id=session_id,
    )
    print("Vector value is created for the line")

    horizontal_plane, vertical_plane, quadrant = calculate_half_plane_and_quadrant(
        x_vect, y_vect
    )
    print(f"Half planes and quadrants: {horizontal_plane, vertical_plane, quadrant}")
    query = """
        MATCH (vector:Vector {vector_id: $vector_id})
        
        MERGE (vertical:VerticalVectorHalfPlane:Feature {value: $vertical_plane, session_id: $session_id})
        ON CREATE SET vertical.samples = [$image_id]
        ON MATCH SET vertical.samples = CASE WHEN $image_id IN vertical.samples THEN vertical.samples ELSE vertical.samples + $image_id END
        
        MERGE (horizontal:HorizontalVectorHalfPlane:Feature {value: $horizontal_plane, session_id: $session_id})
        ON CREATE SET horizontal.samples = [$image_id]
        ON MATCH SET horizontal.samples = CASE WHEN $image_id IN horizontal.samples THEN horizontal.samples ELSE horizontal.samples + $image_id END
        
        MERGE (vector)-[:HAS_VERTICAL_VECTOR_HALF_PLANE]->(vertical)
        MERGE (vector)-[:HAS_HORIZONTAL_VECTOR_HALF_PLANE]->(horizontal)
    """
    tx.run(
        query,
        vector_id=vector.id,
        horizontal_plane=horizontal_plane,
        vertical_plane=vertical_plane,
        image_id=image_id,
        session_id=session_id,
    )

    query = """
        MATCH (vector:Vector {vector_id: $vector_id})
        MERGE (quadrant:Quadrant:Feature {value: $quadrant, session_id: $session_id})
        ON CREATE SET quadrant.samples = [$image_id]
        ON MATCH SET quadrant.samples = CASE WHEN $image_id IN quadrant.samples THEN quadrant.samples ELSE quadrant.samples + $image_id END
        MERGE (vector)-[:HAS_QUADRANT]->(quadrant)
    """
    tx.run(
        query,
        vector_id=vector.id,
        quadrant=quadrant,
        image_id=image_id,
        session_id=session_id,
    )
    print(
        f"Half planes and quadrants are created for the vector: {vector.id} quadrant:{quadrant} "
    )
    return
