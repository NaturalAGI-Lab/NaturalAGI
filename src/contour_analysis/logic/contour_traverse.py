from __future__ import annotations

import logging
from typing import Union, List

from neo4j import ManagedTransaction, Record

from logic.data_saver import save_vectors_data, save_intersection_data
from logic.quadrant_checker import (
    check_quadrant_change,
    mark_quadrant_change,
)
from logic.relative_params_service import calculate_and_set_relative_params
from model.angle_point import AnglePoint
from model.vector_details import VectorDetails
from logic.magnitude_and_direction_service import calculate_magnitude_and_direction

logging.basicConfig(level=logging.INFO)


def process_input_data(
    tx: ManagedTransaction,
    image_id: str,
    angle_points: List[AnglePoint],
    lines: List[VectorDetails],
    session_id: str,
) -> None:
    save_vectors_data(tx, lines, image_id, session_id)
    save_intersection_data(tx, image_id, angle_points, session_id)
    traverse_contour(tx, image_id, angle_points[0], session_id)


def traverse_contour(
    tx: ManagedTransaction, image_id: str, min_angle_point: AnglePoint, session_id: str
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
        processed_vector_ids = [v.id for v in processed_vectors if v is not None]

        logging.info(f"1. processed_vector_ids {processed_vector_ids}")

        result = _get_next_vector(
            tx, processed_angle_points, processed_vector_ids, image_id
        )
        logging.info(f"Result from _get_next_vector: {result}")

        if result is None:
            logging.info("No more vectors to process")
            break

        current_vector, current_angle_point = result

        logging.info(
            f"2. processed_vector_ids {processed_vector_ids}, current {current_vector.id}"
        )

        if current_vector.id not in processed_vector_ids:
            calculate_and_set_relative_params(
                tx, current_vector, current_angle_point, image_id, session_id
            )

        if len(processed_vectors) > 0 and check_quadrant_change(
            tx, processed_vectors[-1].id, current_vector.id
        ):
            print(
                f"mark_quadrant_change: v1:{processed_vectors[-1].id}, v2:{current_vector.id}"
            )
            mark_quadrant_change(
                tx, processed_vectors[-1].id, current_vector.id, image_id, session_id
            )

        if len(processed_vectors) > 0:
            calculate_magnitude_and_direction(
                tx, processed_vectors[-1].id, current_vector.id, image_id, session_id
            )

        processed_vectors.append(current_vector)
        processed_angle_points.append(current_angle_point)

        if current_vector.id in processed_vector_ids:
            logging.info(f"Last vector {current_vector.id} processed")
            logging.info("No more vectors to process")
            break

    # Delete the first critical point at the end of the traversal
    delete_first_critical_point(tx)


def delete_first_critical_point(tx: ManagedTransaction) -> None:
    query = """
        MATCH (cp:CriticalPoint {reason: "First Line"})
        DETACH DELETE cp
    """
    tx.run(query)


def _get_next_vector(
    tx: ManagedTransaction,
    processed_angle_points: list[AnglePoint],
    processed_vectors_ids: list[str],
    image_id: str,
) -> Union[tuple[VectorDetails, AnglePoint], None]:
    """
    Get the next vector to be processed.

    Args:
        tx (ManagedTransaction): The managed transaction object.
        processed_angle_points (list[AnglePoint]): The list of processed angle points.
        processed_vectors_ids (list[str]): The list of processed vector IDs.
        image_id (str): The image id.

    Returns:
        VectorDetails: The next vector to be processed.
    """
    print(
        f"Getting next vector. Passed arguments: processed_angle_points_ids: {processed_angle_points}, processed_vectors_ids: {processed_vectors_ids}"
    )
    if len(processed_vectors_ids) == 0:
        return (
            _get_first_vector(tx, processed_angle_points[0].id, image_id),
            processed_angle_points[0],
        )

    print(
        f"Last vector id:{processed_vectors_ids[-1]}, angle_point_id:{processed_angle_points[-1].id}"
    )

    query = """
        MATCH (v:Vector {vector_id: $last_vector_id})--(ap:AnglePoint {id: $ap_id})--(nextVector:Vector)--(nextAp:AnglePoint),
            (nextVector:Vector)--(coords:Coordinates),
            (nextAp:AnglePoint)--(apLoc:AnglePointCoordinates),
            (nextAp)--(angle:AnglePointAngle),
            (nextVector)--(l:Length)
        WHERE NOT nextAp.id = $ap_id
        RETURN nextVector AS vector, coords AS vector_coords, nextAp AS next_ap, apLoc AS apLoc, l.value AS length,
            angle.angle AS angle
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
        id=result["vector"]["vector_id"],
        x1=result["vector_coords"]["x1"],
        y1=result["vector_coords"]["y1"],
        x2=result["vector_coords"]["x2"],
        y2=result["vector_coords"]["y2"],
        length=result["length"],
    )

    angle_point = AnglePoint(
        x=result["apLoc"]["x"],
        y=result["apLoc"]["y"],
        id=result["next_ap"]["id"],
        angle=result["angle"],
        line1=processed_vectors_ids[-1],
        line2=vector_details.id,
    )

    print(
        f"result of running next vector: {vector_details}, next angle point: {angle_point}"
    )
    return vector_details, angle_point


def _get_first_vector(
    tx: ManagedTransaction, min_angle_point_id: str, image_id: str
) -> VectorDetails:
    """
    Get the first vector of the contour by the clockwise traversal from the minimum angle point.

    Args:
        tx (ManagedTransaction): The managed transaction object.
        min_angle_point_id (str): The minimum angle point id.
        image_id (str): The image id.

    Returns:
        VectorDetails: The first vector of the contour.
    """
    query = """
        MATCH (ap:AnglePoint {id: $id})--(v:Vector)--(coords:Coordinates), (v)--(l:Length)
        WITH v, coords, ap, (ap.x + coords.x1 + coords.x2) AS sum_x, l.value AS length
        ORDER BY sum_x DESC
        LIMIT 1
        MERGE (cp:CriticalPoint:Feature {reason: "First Line"})
        ON CREATE SET cp.samples = [$image_id]
        ON MATCH SET cp.samples = CASE WHEN $image_id IN cp.samples THEN cp.samples ELSE cp.samples + $image_id END
        CREATE (v)-[:IS_CRITICAL_POINT]->(cp)
        RETURN v.vector_id AS id, coords.x1 AS x1, coords.y1 AS y1, coords.x2 AS x2, coords.y2 AS y2, length
    """

    result: Record | None = tx.run(
        query, id=min_angle_point_id, image_id=image_id
    ).single()

    if result is None:
        raise ValueError(f"No vectors found for angle point {min_angle_point_id}")
    else:
        return VectorDetails(
            id=result["id"],
            x1=result["x1"],
            y1=result["y1"],
            x2=result["x2"],
            y2=result["y2"],
            length=result["length"],
        )
