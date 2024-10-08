from __future__ import annotations

import logging
from typing import Union, List, Tuple
import math

from neo4j import ManagedTransaction, Record

from logic.data_saver import save_points_data, save_vectors_data, save_intersection_data
from logic.quadrant_checker import (
    check_quadrant_change,
    mark_quadrant_change,
)
from logic.relative_params_service import calculate_and_set_relative_params
from model.point import IntersectionPoint, EndPoint, Point, CornerPoint
from model.vector_details import VectorDetails
from logic.magnitude_and_direction_service import calculate_magnitude_and_direction

logging.basicConfig(level=logging.DEBUG)


def process_input_data(
    tx: ManagedTransaction,
    image_id: str,
    points: List[Point],
    lines: List[VectorDetails],
    session_id: str,
) -> None:
    intersection_points = [p for p in points if isinstance(p, IntersectionPoint)]
    end_points = [p for p in points if isinstance(p, EndPoint)]
    save_vectors_data(tx, lines, image_id, session_id)
    save_intersection_data(tx, image_id, intersection_points, session_id)
    save_points_data(tx, end_points, image_id, session_id)
    traverse_contour(tx, image_id, session_id, points, lines)


def traverse_contour(
    tx: ManagedTransaction,
    image_id: str,
    session_id: str,
    points: List[Point],
    lines: List[VectorDetails],
) -> None:
    points_dict = {p.id: p for p in points}
    lines_dict = {l.id: l for l in lines}

    start_point = min(points_dict.values(), key=lambda p: (2 * p.x + p.y))

    traversal = []
    visited_points = set()
    visited_lines = set()

    def get_connected_lines(point: Point) -> List[VectorDetails]:
        connected = []
        if isinstance(point, IntersectionPoint):
            line_ids = [point.line1, point.line2]
        elif isinstance(point, EndPoint):
            line_ids = [point.line]
        else:
            line_ids = []
        
        for line_id in line_ids:
            if line_id and line_id not in visited_lines:
                connected.append(lines_dict[line_id])
        return connected

    def get_next_point(line: VectorDetails, current_point: Point) -> Point:
        angle_points = [
            p
            for p in points_dict.values()
            if isinstance(p, IntersectionPoint)
            and (p.line1 == line.id or p.line2 == line.id)
            and p.id != current_point.id
        ]

        if angle_points:
            return angle_points[0]
        else:
            if line.x1 == current_point.x and line.y1 == current_point.y:
                return next(
                    p for p in points_dict.values() if p.x == line.x2 and p.y == line.y2
                )
            else:
                return next(
                    p for p in points_dict.values() if p.x == line.x1 and p.y == line.y1
                )

    def sort_lines_clockwise(
        current_point: Point, connected_lines: List[VectorDetails]
    ) -> List[VectorDetails]:
        def angle_with_x_axis(line: VectorDetails):
            dx = (
                line.x2 - line.x1
                if line.x1 == current_point.x and line.y1 == current_point.y
                else line.x1 - line.x2
            )
            dy = (
                line.y2 - line.y1
                if line.x1 == current_point.x and line.y1 == current_point.y
                else line.y1 - line.y2
            )
            angle = math.atan2(-dy, dx)
            return angle if angle >= 0 else angle + 2 * math.pi

        return sorted(connected_lines, key=angle_with_x_axis)

    def get_coordinates(item: Union[Point, VectorDetails]) -> Tuple[float, float]:
        if isinstance(item, Point):
            return item.x, item.y
        elif isinstance(item, VectorDetails):
            return item.x1, item.y1
        else:
            raise TypeError(f"Unexpected type: {type(item)}")

    def dfs(current_point: Point):
        visited_points.add(current_point.id)
        traversal.append(current_point)

        connected_lines = get_connected_lines(current_point)
        sorted_lines = sort_lines_clockwise(current_point, connected_lines)

        for line in sorted_lines:
            if line.id not in visited_lines:
                visited_lines.add(line.id)
                traversal.append(line)
                
                # Calculate and set relative parameters for the current line
                calculate_and_set_relative_params(tx, line, current_point, image_id, session_id)
                
                if len(traversal) > 2:
                    last_vector = traversal[-3] if isinstance(traversal[-3], VectorDetails) else traversal[-2]
                    last_point = traversal[-3] if isinstance(traversal[-3], Point) else traversal[-4]
                    
                    if check_quadrant_change(tx, last_vector.id, line.id):
                        mark_quadrant_change(tx, last_vector.id, line.id, image_id, session_id)
                    
                    last_vector_start = get_coordinates(last_vector)
                    last_vector_end = (last_vector.x2, last_vector.y2)
                    last_point_coords = get_coordinates(last_point)
                    current_vector_start = (line.x1, line.y1)
                    current_vector_end = (line.x2, line.y2)
                    
                    calculate_magnitude_and_direction(
                        tx,
                        last_vector_start,
                        last_vector_end,
                        last_point_coords,
                        current_vector_start,
                        current_vector_end,
                        last_vector.id,
                        line.id,
                        image_id,
                        session_id,
                    )
                
                next_point = get_next_point(line, current_point)
                if next_point.id not in visited_points:
                    dfs(next_point)

    dfs(start_point)

    return traversal
