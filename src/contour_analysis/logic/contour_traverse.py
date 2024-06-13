from __future__ import annotations

import logging
import math
from typing import Union, List

from converter.angle_point_converter import AnglePointConverter
from logic.quadrant_checker import (
    check_quadrant_change,
    mark_quadrant_change,
)
from logic.relative_params_service import (
    calculate_and_set_relative_params,
    # _create_relative_characteristics
)
from model.angle_point import AnglePoint
from model.vector_details import VectorDetails
from neo4j import ManagedTransaction, Record

logging.basicConfig(level=logging.INFO)


def process_input_data(
        tx: ManagedTransaction,
        input_data: json
) -> None:
    query = """
        MATCH (n)
        RETURN COUNT(n) > 0 AS hasNodes
     """
    result: bool | None = tx.run(query).single()["hasNodes"]

    if result:
        logging.info(f"Data is already there in the DB {input_data['image_id']}")
        lines = input_data['lines']
        angle_points = input_data['angle_points']
        print(lines)
        for i in range(len(lines)):
            _execute_add_lines_query(tx, lines, input_data["image_id"], i)
            persist_intersection_data(tx, input_data["image_id"], lines, input_data["angle_points"], i)
            traverse_contour(tx, input_data["image_id"], angle_points[0], i)
            lines = [lines[-1]] + lines[:-1]
            mark_first_line(tx, i)
    else:
        logging.info(f"No data in the DB so far. Image {input_data['image_id']} will be considered as the Concept one")
        _execute_add_lines_query(tx, input_data["lines"], input_data["image_id"], 'C')
        persist_intersection_data(tx, input_data["image_id"], input_data["lines"], input_data["angle_points"], 'C')

        angle_points: List[AnglePoint] = AnglePointConverter.dict_to_angle_point(input_data['angle_points'])
        traverse_contour(tx, input_data["image_id"], angle_points[0], 0)

        mark_first_line(tx, 'C')


def mark_first_line(tx, node_index):
    query = f"""
        MATCH (apStartingPoint:StartingPoint {{round_id: '{node_index}'}})--(ap:AnglePoint)--(v:Vector)--(loc:Location)--(coords:Coordinates)
        WITH v, (ap.x + coords.x1 + coords.x2) AS sum_x
        ORDER BY sum_x DESC
        LIMIT 1
        CREATE (cp:CriticalPoint {{reason: "First Line"}})
        CREATE (cp)<-[:IS_CRITICAL_POINT]-(v)
    """
    return tx.run(query)


def compare_and_find_best_round(
        tx: ManagedTransaction
) -> None:
    query = """
        MATCH (a:mandatory)-[:REL_TYPE]->(subA)
        WHERE (a)-[:GRAPH]->(:GraphA) AND NOT EXISTS (
            MATCH (b:mandatory)-[:REL_TYPE]->(subB)
            WHERE (b)-[:GRAPH]->(:GraphB) AND subA.prop = subB.prop
        )
        RETURN COUNT(DISTINCT subA) AS UniqueSubNodesInGraphA
    
        // Find sub-nodes in Graph B not in Graph A
        MATCH (b:mandatory)-[:REL_TYPE]->(subB)
        WHERE (b)-[:GRAPH]->(:GraphB) AND NOT EXISTS (
            MATCH (a:mandatory)-[:REL_TYPE]->(subA)
            WHERE (a)-[:GRAPH]->(:GraphA) AND subB.prop = subA.prop
        )
        RETURN COUNT(DISTINCT subB) AS UniqueSubNodesInGraphB
    """


def _execute_add_lines_query(tx, lines, image_id, node_index):
    query = ""
    for line in lines:
        line_id = line["id"]
        x1 = int(line['x1'])
        y1 = int(line['y1'])
        x2 = int(line['x2'])
        y2 = int(line['y2'])

        temp_line_id = replace_dashes_with_underscores(line_id)
        query += f"""
            (v{temp_line_id}:Vector {{image_id:'{image_id}', vector_id: '{line_id}', round_id: '{node_index}'}}), 
            
            (length{temp_line_id}:Length {{vector_id:'{line_id}', round_id: '{node_index}'}}), 
            (absolute{temp_line_id}:Absolute {{vector_id:'{line_id}', value:{round(math.dist([x1, y1], [x2, y2]))}, round_id: '{node_index}'}}), 
            (v{temp_line_id})-[:HAS_LENGTH]->(length{temp_line_id}), 
            (length{temp_line_id})-[:HAS_ABSOLUTE]->(absolute{temp_line_id}), 

            (orientation{temp_line_id}:Orientation {{vector_id:'{line_id}', round_id: '{node_index}'}}),
            (angle{temp_line_id}:Angle {{vector_id:'{line_id}', value:{calculate_abs_angle(x1, y1, x2, y2)}, round_id: '{node_index}'}}), 
            (v{temp_line_id})-[:HAS_ORIENTATION]->(orientation{temp_line_id}), 
            (orientation{temp_line_id})-[:HAS_ANGLE]->(angle{temp_line_id}),

            (location{temp_line_id}:Location {{vector_id:'{line_id}', round_id: '{node_index}'}}),
            (coordinates{temp_line_id}:Coordinates {{vector_id:'{line_id}', x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, round_id: '{node_index}'}}),
            (v{temp_line_id})-[:HAS_LOCATION]->(location{temp_line_id}), 
            (location{temp_line_id})-[:HAS_COORDINATES]->(coordinates{temp_line_id}),
        """
    result = tx.run(f"CREATE {query.strip().strip(',')}")
    return result


def check_if_starting_point(i, j, node_index):
    if i == 0 and j == 1:
        return f"""CREATE (apStartingPoint:StartingPoint {{starting_point: 'START', round_id: '{node_index}'}})
                  CREATE (ap)-[:IS_CRITICAL_POINT]->(apStartingPoint)"""
    else:
        return ''


def replace_dashes_with_underscores(input_string):
    """Replace all dashes '-' with underscores '_' in the given string."""
    return input_string.replace('-', '_')


def persist_intersection_data(
        tx,
        image_id,
        lines,
        angle_points,
        node_index
) -> None:
    intersection_data = []

    for i in range(len(lines)):
        line1 = lines[i]

        for j in range(i + 1, len(lines)):
            line2 = lines[j]

            line1_line2_angle_point = angle_points[0]
            for angle_point in angle_points:
                if (angle_point["line1"] == line1['id'] and angle_point["line2"] == line2['id']) or (
                        angle_point["line2"] == line1['id'] and angle_point["line1"] == line2['id']):
                    line1_line2_angle_point = angle_point

            x1_1 = int(line1['x1'])
            y1_1 = int(line1['y1'])
            x2_1 = int(line1['x2'])
            y2_1 = int(line1['y2'])

            x1_2 = int(line2['x1'])
            y1_2 = int(line2['y1'])
            x2_2 = int(line2['x2'])
            y2_2 = int(line2['y2'])

            line1_coords = (x1_1, y1_1, x2_1, y2_1)
            # line1_coords = (int(line1['x1']), int(line1['y1']), int(line1['x2']), int(line1['y2']))
            line2_coords = (x1_2, y1_2, x2_2, y2_2)
            # line2_coords = (int(line2['x1']), int(line2['y1']), int(line2['x2']), int(line2['y2']))

            intersection = line_intersection(line1_coords, line2_coords)

            if intersection:
                angle = calculate_angle(x1_1, x2_1, y1_1, y2_1, x1_2, x2_2, y1_2, y2_2)
                intersection_data.append({
                    'line1_id': line1['id'],
                    'line2_id': line2['id'],
                    'intersection': {'x': intersection[0], 'y': intersection[1]},
                    'angle': angle,
                    'angle_point_id': line1_line2_angle_point['id']
                })

            query = f"""
                    UNWIND $intersection_data AS data
                    MERGE (ap:AnglePoint {{id: data.angle_point_id, image_id: $image_id, round_id: '{node_index}'}})
                    MERGE (apCoords:AnglePointCoordinates {{x: data.intersection.x, y: data.intersection.y, round_id: '{node_index}'}}) 
                    {(check_if_starting_point(i, j, node_index))}
                    MERGE (ap)-[:HAS_COORDINATES]->(apCoords)
                    MERGE (apAngle:AnglePointAngle {{angle: data.angle, round_id: '{node_index}'}})
                    MERGE (ap)-[:HAS_ANGLE]->(apAngle)
        
                    WITH ap, data
                    MATCH (vector1:Vector {{vector_id: data.line1_id, round_id: '{node_index}'}})
                    MATCH (vector2:Vector {{vector_id: data.line2_id, round_id: '{node_index}'}})
                    MERGE (vector1)-[:HAS_ANGLE_POINT]->(ap)
                    MERGE (vector2)-[:HAS_ANGLE_POINT]->(ap)
                    """
            tx.run(query, intersection_data=intersection_data, image_id=image_id)


def traverse_contour(
        tx: ManagedTransaction,
        image_id: str,
        min_angle_point: AnglePoint,
        node_index
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

        logging.info(f"1. processed_vector_ids {processed_vector_ids}")

        result = _get_next_vector(tx, processed_angle_points, processed_vector_ids, node_index)
        logging.info(f"Result from _get_next_vector: {result}")

        if result is None:
            logging.info("No more vectors to process")
            break

        current_vector, current_angle_point = result

        logging.info(f"2. processed_vector_ids {processed_vector_ids}, current {current_vector.uuid}")

        logging.info(f"current_angle_point: {current_angle_point}")
        calculate_and_set_relative_params(tx, current_vector, current_angle_point)

        if len(processed_vectors) > 0 and check_quadrant_change(
                tx, processed_vectors[-1].uuid, current_vector.uuid
        ):
            print(f"mark_quadrant_change: v1:{processed_vectors[-1].uuid}, v2:{current_vector.uuid}")
            mark_quadrant_change(tx, processed_vectors[-1].uuid, current_vector.uuid)

        # if len(processed_vectors) > 0:
        #     calculate_magnitude_and_direction(
        #         tx, processed_vectors[-1].uuid, current_vector.uuid
        #     )

        processed_vectors.append(current_vector)
        processed_angle_points.append(current_angle_point.id)

        if len(processed_vector_ids) == 3:
            logging.info(f"Last vector {current_vector.uuid} processed")
            logging.info("No more vectors to process")
            break


def _get_next_vector(
        tx: ManagedTransaction,
        processed_angle_points: list[AnglePoint],
        processed_vectors_ids: list[str],
        node_index
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
    print(
        f"Getting next vector. Passed arguments: processed_angle_points_ids: {processed_angle_points}, processed_vectors_ids: {processed_vectors_ids}"
    )
    if len(processed_vectors_ids) == 0:
        return (
            _get_first_vector(tx, processed_angle_points[0].id),
            processed_angle_points[0],
        )

    print(f"Last vector id:{processed_vectors_ids[-1]}, angle_point_id:{get_attribute(processed_angle_points, 'id')}")

    query = """
        MATCH (v:Vector {vector_id: $last_vector_id})--(ap:AnglePoint {id: $ap_id})--(nextVector:Vector)--(nextAp:AnglePoint),
            (nextVector:Vector)--(location:Location)--(coords:Coordinates),
            (nextAp:AnglePoint)--(apLoc:AnglePointCoordinates)
        WHERE NOT nextAp.id = $ap_id
        RETURN nextVector.vector_id AS uuid, coords.x1 AS x1, coords.y1 AS y1, coords.x2 AS x2, coords.y2 AS y2, apLoc.x AS ap_x, apLoc.y AS ap_y, nextAp.id AS ap_id
    """
    result: Record | None = tx.run(
        query,
        last_vector_id=processed_vectors_ids[-1],
        ap_id=get_attribute(processed_angle_points, 'id'),
        processed_vectors_ids=processed_vectors_ids,
        # round_id=node_index
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
    print(f"result of running next vector: {vector_details}, next angle point: {angle_point}")
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
        MATCH (ap:AnglePoint {id: $id})--(v:Vector)--(loc:Location)--(coords:Coordinates)
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


def line_intersection(line1, line2):
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denominator == 0:
        return None

    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator

    # Check if the intersection point is within the boundaries of both lines
    # if min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2) and \
    #         min(x3, x4) <= px <= max(x3, x4) and min(y3, y4) <= py <= max(y3, y4):
    if True:
        return [int(px), int(py)]
    else:
        return None


def calculate_abs_angle(x1, y1, x2, y2):
    angle_radians = math.atan2(y2 - y1, x2 - x1)
    angle_degrees = math.degrees(angle_radians)
    return abs(angle_degrees)


def calculate_angle(x1_1, x2_1, y1_1, y2_1, x1_2, x2_2, y1_2, y2_2):
    dx1 = x2_1 - x1_1
    dy1 = y2_1 - y1_1
    dx2 = x2_2 - x1_2
    dy2 = y2_2 - y1_2

    angle1 = math.atan2(dy1, dx1)
    angle2 = math.atan2(dy2, dx2)
    angle = abs(angle1 - angle2)

    if angle > math.pi:
        angle = 2 * math.pi - angle

    # Ensuring the angle is always the interior angle
    if angle > math.pi / 2:
        angle = math.pi - angle

    angle = int(math.degrees(angle))  # Convert to degrees

    return angle


def get_attribute(obj, attr):
    if isinstance(obj, dict):
        return obj.get(attr, None)  # None is default if key doesn't exist
    else:
        return getattr(obj, attr, None)  # None is default if attribute doesn't exist
