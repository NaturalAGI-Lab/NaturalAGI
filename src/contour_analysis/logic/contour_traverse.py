import logging
from typing import Union
from neo4j import ManagedTransaction, Record

from logic.magnitude_and_direction_service import (
    calculate_magnitude_and_direction,
)
from logic.quadrant_checker import (
    check_quadrant_change,
    mark_quadrant_change,
)
from logic.relative_params_service import (
    calculate_and_set_relative_params,
)
from model.angle_point import AnglePoint
from model.vector_details import VectorDetails

logging.basicConfig(level=logging.INFO)


def find_starting_point(
    tx: ManagedTransaction, image_id: str
) -> Union[AnglePoint, None]:
    logging.info(f"Finding starting point for image {image_id}")

    query = """
        MATCH (apLoc:AnglePointCoordinates)--(n:AnglePoint {image_id: $image_id})
        WITH apLoc, n
        ORDER BY apLoc.y, apLoc.x
        LIMIT 1
        MERGE (criticalPoint: CriticalPoint {reason: "First point"})
        MERGE (criticalPoint)<-[:IS_CRITICAL_POINT]-(n)
        RETURN {x: apLoc.x, y: apLoc.y, id: n.id} AS MinAnglePoint
    """
    result: Record | None = tx.run(query, image_id=image_id).single()

    if result is None:
        return None

    min_angle_point = AnglePoint(
        x=result["MinAnglePoint"]["x"],
        y=result["MinAnglePoint"]["y"],
        id=result["MinAnglePoint"]["id"],
    )
    logging.info(f"Found starting point for image {image_id}: {min_angle_point}")
    return min_angle_point


def traverse_contour(
    tx: ManagedTransaction,
    image_id: str,
    min_angle_point: AnglePoint,
) -> None:
    """
    Traverses the contour for a given image.

    Args:
        tx (ManagedTransaction): The managed transaction object.
        image_id (str): The ID of the image.
        min_angle_point (AnglePoint): The minimum angle point (starting point for traversal).
    Returns:
        None
    """
    logging.info(f"Traversing contour for image {image_id}")

    processed_angle_points: list[AnglePoint] = [min_angle_point]
    processed_vectors: list[VectorDetails] = []

    while True:
        processed_vector_ids = [v.uuid for v in processed_vectors if v is not None]

        result = _get_next_vector(tx, processed_angle_points, processed_vector_ids)
        logging.debug(f"Result from _get_next_vector: {result}")

        if result is None:
            logging.info("No more vectors to process")
            break

        current_vector, current_angle_point = result

        calculate_and_set_relative_params(tx, current_vector, current_angle_point)

        if len(processed_vectors) > 0 and check_quadrant_change(
            tx, processed_vectors[-1].uuid, current_vector.uuid
        ):
            mark_quadrant_change(tx, processed_vectors[-1].uuid, current_vector.uuid)

        if len(processed_vectors) > 0:
            calculate_magnitude_and_direction(
                tx, processed_vectors[-1].uuid, current_vector.uuid
            )

        processed_vectors.append(current_vector)
        processed_angle_points.append(current_angle_point)

        if current_vector.uuid in processed_vector_ids:
            logging.info(f"Last vector {current_vector.uuid} processed")
            logging.info("No more vectors to process")
            break


def _get_next_vector(
    tx: ManagedTransaction,
    processed_angle_points: list[AnglePoint],
    processed_vectors_ids: list[str],
) -> Union[tuple[VectorDetails, AnglePoint], None]:
    """
    Get the next vector to be processed.

    Args:
        tx (ManagedTransaction): The managed transaction object.
        processed_angle_points (list[AnglePoint]): The list of processed angle points.
        processed_vectors_ids (list[str]): The list of processed vector IDs.

    Returns:
        VectorDetails: The next vector to be processed.
    """
    logging.debug(
        f"Getting next vector. Passed arguments: processed_angle_points_ids: {processed_angle_points}, processed_vectors_ids: {processed_vectors_ids}"
    )
    if len(processed_vectors_ids) == 0:
        return (
            _get_first_vector(tx, processed_angle_points[0].id),
            processed_angle_points[0],
        )

    query = """
        MATCH (v:Vector {vector_id: $last_vector_id})--(ap:AnglePoint {id: $ap_id})--(nextVector:Vector)--(nextAp:AnglePoint), 
            (nextVector:Vector)--(coords:VectorCoordinates), 
            (nextAp:AnglePoint)--(apLoc:AnglePointCoordinates)
        WHERE NOT nextAp.id = $ap_id
        RETURN nextVector.vector_id AS uuid, coords.x1 AS x1, coords.y1 AS y1, coords.x2 AS x2, coords.y2 AS y2, apLoc.x AS ap_x, apLoc.y AS ap_y, nextAp.id AS ap_id
    """
    result: Record | None = tx.run(
        query,
        last_vector_id=processed_vectors_ids[-1],
        ap_id=processed_angle_points[-1].id,
        processed_vectors_ids=processed_vectors_ids,
    ).single()

    if result is None:
        return None

    vector_details = VectorDetails(
        uuid=result["uuid"],
        x1=result["x1"],
        y1=result["y1"],
        x2=result["x2"],
        y2=result["y2"],
    )
    angle_point = AnglePoint(x=result["ap_x"], y=result["ap_y"], id=result["ap_id"])
    return vector_details, angle_point


def _get_first_vector(tx: ManagedTransaction, min_angle_point_id: int) -> VectorDetails:
    """
    Get the first vector of the contour by the clockwise traversal from the minimum angle point.

    Args:
        tx (ManagedTransaction): The managed transaction object.
        min_angle_point (AnglePoint): The minimum angle point.

    Returns:
        VectorDetails: The first vector of the contour.
    """
    query = """
        MATCH (ap:AnglePoint {id: $id})--(v:Vector)--(coords:VectorCoordinates)
        WITH v, coords, ap, (ap.x + coords.x1 + coords.x2) AS sum_x
        ORDER BY sum_x DESC
        LIMIT 1
        MERGE (cp:CriticalPoint {reason: "First Line"})
        MERGE (cp)<-[:IS_CRITICAL_POINT]-(v)
        RETURN v.vector_id AS uuid, coords.x1 AS x1, coords.y1 AS y1, coords.x2 AS x2, coords.y2 AS y2
    """

    result: Record | None = tx.run(query, id=min_angle_point_id).single()

    if result is None:
        raise ValueError(f"No vectors found for angle point {min_angle_point_id}")
    else:
        return VectorDetails(
            uuid=result["uuid"],
            x1=result["x1"],
            y1=result["y1"],
            x2=result["x2"],
            y2=result["y2"],
        )
