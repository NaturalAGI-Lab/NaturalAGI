import logging
import math
from typing import List

from neo4j import ManagedTransaction

from model.angle_point import AnglePoint
from model.vector_details import VectorDetails


def save_vectors_data(tx, vectors: List[VectorDetails], image_id: str, node_index):
    for vector in vectors:
        angle = calculate_abs_angle(vector.x1, vector.y1, vector.x2, vector.y2)
        tx.run(
            """CREATE
            (v:Vector {image_id: $image_id, vector_id: $vector_id, round_id: $node_index}), 
    
            (length:Length {vector_id: $vector_id, value: $length, round_id: $node_index}), 
            (v)-[:HAS_LENGTH]->(length),  
    
            (angle:Angle {vector_id: $vector_id, value: $angle, round_id: $node_index}), 
            (v)-[:HAS_ANGLE]->(angle),
    
            (coordinates:Coordinates {vector_id:$vector_id, x1: $x1, y1: $y1, x2: $x2, y2: $y2, round_id: $node_index}),
            (v)-[:HAS_COORDINATES]->(coordinates)
            """, image_id=image_id, node_index=node_index, vector_id=vector.id, length=vector.length, angle=angle,
            x1=vector.x1, y1=vector.y1, x2=vector.x2, y2=vector.y2)


def save_intersection_data(tx: ManagedTransaction,
                           image_id: str,
                           angle_points: List[AnglePoint],
                           node_index):
    query: str = """
            UNWIND $angle_points AS data
            MERGE (ap:AnglePoint {id: data.id, image_id: $image_id, round_id: $node_index})
            MERGE (apCoords:AnglePointCoordinates {x: data.x, y: data.y, round_id: $node_index}) 
            MERGE (ap)-[:HAS_COORDINATES]->(apCoords)
            MERGE (apAngle:AnglePointAngle {angle: data.angle, round_id: $node_index})
            MERGE (ap)-[:HAS_ANGLE]->(apAngle)

            WITH ap, data
            MATCH (vector1:Vector {vector_id: data.line1, round_id: $node_index})
            MATCH (vector2:Vector {vector_id: data.line2, round_id: $node_index})
            MERGE (vector1)-[:HAS_ANGLE_POINT]->(ap)
            MERGE (vector2)-[:HAS_ANGLE_POINT]->(ap)
        """
    points_ = [vars(angle_point) for angle_point in angle_points]
    logging.info(f"Saving intersection data for image {image_id} with {points_} angle points")
    tx.run(query, angle_points=points_, image_id=image_id,
           node_index=node_index)


def calculate_abs_angle(x1, y1, x2, y2):
    angle_radians = math.atan2(y2 - y1, x2 - x1)
    angle_degrees = math.degrees(angle_radians)
    return abs(angle_degrees)
