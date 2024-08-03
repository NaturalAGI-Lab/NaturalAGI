import logging
from typing import Union

import numpy as np
from neo4j import ManagedTransaction, Record

from logic.magnitude_comparator import (
    compare_vector_magnitude_and_create_nodes,
)

logging.basicConfig(level=logging.DEBUG)


def calculate_magnitude_and_direction(
        tx: ManagedTransaction,
        last_vector_id: str,
        next_vector_id: str,
        image_id: str,
):
    if last_vector_id is None:
        logging.debug("Can't compare the first vector... Skipping first iteration")
        return

    last_direction = get_last_direction(tx, last_vector_id)
    current_direction = calculate_direction(tx, last_vector_id, next_vector_id)
    
    if current_direction is None:
        logging.warning(f"Could not calculate direction for vectors {last_vector_id} and {next_vector_id}")
        return

    add_direction(tx, last_vector_id, next_vector_id, current_direction, image_id)

    if last_direction and last_direction != current_direction:
        # If there's a direction change, create a CriticalPoint at the angle between the vectors
        create_critical_point(tx, last_vector_id, next_vector_id, image_id)
    else:
        logging.info("No changes in directions")
    return compare_vector_magnitude_and_create_nodes(tx, last_vector_id, next_vector_id, image_id)


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
        tx: ManagedTransaction,
        vector1_id: str,
        vector2_id: str,
) -> Union[str, None]:
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_ANGLE_POINT]->(ap:AnglePoint)<-[:HAS_ANGLE_POINT]-(v2:Vector {vector_id: $vector2_id})
        MATCH (v1)-[:HAS_VECTOR_VALUE]->(value1:VectorValue)
        MATCH (v2)-[:HAS_VECTOR_VALUE]->(value2:VectorValue)
        RETURN 
            value1.x AS x1, value1.y AS y1,
            value2.x AS x2, value2.y AS y2
    """
    record = tx.run(
        query,
        vector1_id=vector1_id,
        vector2_id=vector2_id,
    ).single()

    if record:
        x1, y1, x2, y2 = record["x1"], record["y1"], record["x2"], record["y2"]
        
        # Calculate vectors
        v1 = [x2 - x1, y2 - y1]
        v2 = [x2 - x1, y2 - y1]

        logging.debug(f"Vectors: v1={v1}, v2={v2}")
        cross_product = np.cross(v1, v2)
        
        if cross_product < 0:
            return "CounterClockwise"
        elif cross_product > 0:
            return "Clockwise"
        else:
            return "Collinear"
    else:
        logging.warning("No matching vectors found in the database.")
        return None


def add_direction(tx, vector1_id: str, vector2_id: str, direction: str, image_id: str):
    logging.debug(f"Adding direction: {direction} to the vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_ANGLE_POINT]->(ap:AnglePoint)<-[:HAS_ANGLE_POINT]-(v2:Vector {vector_id: $vector2_id})
        MERGE (vd:VectDirection:Feature {direction: $direction})
        ON CREATE SET vd.samples = [$image_id]
        ON MATCH SET vd.samples = CASE WHEN $image_id IN vd.samples THEN vd.samples ELSE vd.samples + [$image_id] END
        CREATE (v1)-[:HAS_DIRECTION]->(vd)-[:HAS_DIRECTION]->(v2)
    """
    tx.run(query, vector1_id=vector1_id, vector2_id=vector2_id, direction=direction, image_id=image_id)


def create_critical_point(tx, vector1_id: str, vector2_id: str, image_id: str):
    logging.info("Finding angle point between two vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_ANGLE_POINT]->(ap:AnglePoint)<-[:HAS_ANGLE_POINT]-(v2:Vector {vector_id: $vector2_id})
        MERGE (cp:CriticalPoint:Feature {reason: "Direction Change"})-[:IS_CRITICAL_POINT]->(ap)
        ON CREATE SET cp.samples = [$image_id]
        ON MATCH SET cp.samples = CASE WHEN $image_id IN cp.samples THEN cp.samples ELSE cp.samples + [$image_id] END
    """
    tx.run(query, vector1_id=vector1_id, vector2_id=vector2_id, image_id=image_id)