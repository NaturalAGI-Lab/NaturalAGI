import logging
from typing import Union

import numpy as np
from neo4j import ManagedTransaction, Record

from logic.magnitude_comparator import (
    compare_vector_magnitude_and_create_nodes,
)

logging.basicConfig(level=logging.INFO)


def calculate_magnitude_and_direction(
        tx: ManagedTransaction,
        last_vector_start: tuple[float, float],
        last_vector_end: tuple[float, float],
        angle_point: tuple[float, float],
        current_vector_start: tuple[float, float],
        current_vector_end: tuple[float, float],
        last_vector_id: str,
        next_vector_id: str,
        image_id: str,
        session_id: str
):
    if last_vector_id is None:
        logging.info("Can't compare the first vector... Skipping first iteration")
        return

    last_direction = get_last_direction(tx, last_vector_id)
    logging.info(f"Last direction: {last_direction}")
    
    current_direction = calculate_direction(
        last_vector_start,
        last_vector_end,
        angle_point,
        current_vector_start,
        current_vector_end
    )
    logging.info(f"Current direction: {current_direction}")
    
    if current_direction is None:
        logging.warning(f"Could not calculate direction for vectors {last_vector_id} and {next_vector_id}")
        return

    add_direction(tx, last_vector_id, next_vector_id, current_direction, image_id, session_id)

    if last_direction and last_direction != current_direction:
        # If there's a direction change, create a CriticalPoint at the angle between the vectors
        create_critical_point(tx, last_vector_id, next_vector_id, image_id, session_id)
    else:
        logging.info("No changes in directions")
    return compare_vector_magnitude_and_create_nodes(tx, last_vector_id, next_vector_id, image_id, session_id)


def get_last_direction(tx: ManagedTransaction, last_vector_id: str) -> Union[str, None]:
    query = """
        MATCH (:Vector {vector_id: $last_vector_id})--(vd:VectDirection)
        RETURN vd.direction AS direction
    """
    result: Record | None = tx.run(query, last_vector_id=last_vector_id).single()
    if result is None:
        return None
    return result["direction"]


def calculate_direction(
        last_vector_start: tuple[float, float],
        last_vector_end: tuple[float, float],
        angle_point: tuple[float, float],
        current_vector_start: tuple[float, float],
        current_vector_end: tuple[float, float]
) -> str:
    logging.info(f"All points: last_vector_start={last_vector_start}, last_vector_end={last_vector_end}, angle_point={angle_point}, current_vector_start={current_vector_start}, current_vector_end={current_vector_end}")
    
    # Define a threshold for coordinate approximation
    threshold = 5
    
    # Determine the starting point and endpoint for each vector
    if abs(last_vector_start[0] - angle_point[0]) < threshold and abs(last_vector_start[1] - angle_point[1]) < threshold:
        logging.info("Last vector start is approximately equal to the angle point")
        last_vector_start = last_vector_end
    if abs(current_vector_start[0] - angle_point[0]) < threshold and abs(current_vector_start[1] - angle_point[1]) < threshold:
        logging.info("Current vector start is approximately equal to the angle point")
        current_vector_end = current_vector_start

    logging.info(f"Last vector start: {last_vector_start}, Current vector end: {current_vector_end}")
    
    # Calculate vectors
    v1 = [angle_point[0] - last_vector_start[0], angle_point[1] - last_vector_start[1]]
    v2 = [current_vector_end[0] - angle_point[0], current_vector_end[1] - angle_point[1]]

    logging.info(f"Vectors: v1={v1}, v2={v2}")
    cross_product = np.cross(v1, v2)
    
    if cross_product < 0:
        return "CounterClockwise"
    elif cross_product > 0:
        return "Clockwise"
    else:
        return "Collinear"


def add_direction(tx, vector1_id: str, vector2_id: str, direction: str, image_id: str, session_id: str):
    logging.info(f"Adding direction: {direction} to the vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_POINT]->(ap:IntersectionPoint)<-[:HAS_POINT]-(v2:Vector {vector_id: $vector2_id})
        MERGE (vd:VectDirection:Feature {direction: $direction, session_id: $session_id})
        ON CREATE SET vd.samples = [$image_id]
        ON MATCH SET vd.samples = CASE WHEN $image_id IN vd.samples THEN vd.samples ELSE vd.samples + [$image_id] END
        CREATE (v1)-[:HAS_DIRECTION]->(vd)-[:HAS_DIRECTION]->(v2)
    """
    tx.run(query, vector1_id=vector1_id, vector2_id=vector2_id, direction=direction, image_id=image_id, session_id=session_id)


def create_critical_point(tx, vector1_id: str, vector2_id: str, image_id: str, session_id: str):
    logging.info("Finding angle point between two vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_POINT]->(ap:IntersectionPoint)<-[:HAS_POINT]-(v2:Vector {vector_id: $vector2_id})
        MERGE (cp:CriticalPoint:Feature {reason: "Direction Change", session_id: $session_id})-[:IS_CRITICAL_POINT]->(ap)
        ON CREATE SET cp.samples = [$image_id]
        ON MATCH SET cp.samples = CASE WHEN $image_id IN cp.samples THEN cp.samples ELSE cp.samples + [$image_id] END
    """
    tx.run(query, vector1_id=vector1_id, vector2_id=vector2_id, image_id=image_id, session_id=session_id)