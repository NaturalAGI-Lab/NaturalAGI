import logging
from typing import Union

import numpy as np

from logic.magnitude_comparator import (
    compare_vector_magnitude_and_create_nodes,
)
from neo4j import ManagedTransaction, Record


def calculate_magnitude_and_direction(
    tx: ManagedTransaction,
    last_vector_id: str,
    next_vector_id: str,
):
    if last_vector_id is None:
        logging.debug("Can't compare the first vector... Skipping first iteration")
        return

    last_direction = get_last_direction(tx, last_vector_id)
    current_direction = calculate_direction(tx, last_vector_id, next_vector_id)
    add_direction(tx, last_vector_id, next_vector_id, current_direction)

    if last_direction and last_direction != current_direction:
        # If there's a direction change, create a CriticalPoint at the angle between the vectors
        create_critical_point(tx, last_vector_id, next_vector_id)
    else:
        logging.info("No changes in directions")
    return compare_vector_magnitude_and_create_nodes(tx, last_vector_id, next_vector_id)


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
            value1.x AS x_v1, value1.y AS y_v1,
            value2.x AS x_v2, value2.y AS y_v2
    """
    record = tx.run(
        query,
        vector1_id=vector1_id,
        vector2_id=vector2_id,
    ).single()

    if record:
        # Convert Record to dictionary for modification
        result = dict(record)
        logging.info(result)

        v1 = [result["x_v1"], result["y_v1"]]
        v2 = [result["x_v2"], result["y_v2"]]

        logging.debug(f"Cross product for: {v1, v2}")
        cross_product = np.cross(v1, v2)
        current_direction = (
            "CounterClockwise"
            if cross_product < 0
            else "Clockwise" if cross_product > 0 else "Collinear"
        )

        return current_direction
    else:
        logging.info("No matching vectors found in the database.")
        return None


def add_direction(tx, vector1_id: str, vector2_id: str, direction: str):
    logging.debug(f"Adding direction: {direction} to the vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_ANGLE_POINT]->(ap:AnglePoint)<-[:HAS_ANGLE_POINT]-(v2:Vector {vector_id: $vector2_id})--(v2:Vector)
        MERGE (vd:VectDirection {direction: $direction})
        MERGE (v1)-[:HAS_DIRECTION]->(vd)-[:HAS_DIRECTION]->(v2)
    """
    tx.run(query, vector1_id=vector1_id, vector2_id=vector2_id, direction=direction)


def create_critical_point(tx, vector1_id: str, vector2_id: str):
    logging.info("Finding angle point between two vectors")
    query = """
        MATCH (v1:Vector {vector_id: $vector1_id})-[:HAS_ANGLE_POINT]->(ap:AnglePoint)<-[:HAS_ANGLE_POINT]-(v2:Vector {vector_id: $vector2_id})
        MERGE (cp:CriticalPoint {reason: "Direction Change"})
        MERGE (cp)-[:IS_CRITICAL_POINT]-(ap)
        RETURN cp
    """
    tx.run(query, vector1_id=vector1_id, vector2_id=vector2_id).single()
