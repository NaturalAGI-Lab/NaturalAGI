import logging
import math
from typing import List

from neo4j import ManagedTransaction

from model.angle_point import AnglePoint
from model.vector_details import VectorDetails


def save_vectors_data(tx, vectors: List[VectorDetails], image_id: str):
    for vector in vectors:
        angle = calculate_abs_angle(vector.x1, vector.y1, vector.x2, vector.y2)
        tx.run(
            """
            // Create or match Length node
            MERGE (length:Length:Feature {value: $length})
            ON CREATE SET length.samples = [$image_id]
            ON MATCH SET length.samples = CASE WHEN $image_id IN length.samples THEN length.samples ELSE length.samples + $image_id END
            
            // Create or match Angle node
            MERGE (angle:Angle:Feature {value: $angle})
            ON CREATE SET angle.samples = [$image_id]
            ON MATCH SET angle.samples = CASE WHEN $image_id IN angle.samples THEN angle.samples ELSE angle.samples + $image_id END
            
            // Create or match Coordinates node
            MERGE (coordinates:Coordinates:Feature {x1: $x1, y1: $y1, x2: $x2, y2: $y2})
            ON CREATE SET coordinates.samples = [$image_id]
            ON MATCH SET coordinates.samples = CASE WHEN $image_id IN coordinates.samples THEN coordinates.samples ELSE coordinates.samples + $image_id END
            
            // Always create a new Vector node
            CREATE (v:Vector {image_id: $image_id, vector_id: $vector_id, samples: [$image_id]})
            CREATE (v)-[:HAS_ANGLE]->(angle)
            CREATE (v)-[:HAS_LENGTH]->(length)
            CREATE (v)-[:HAS_COORDINATES]->(coordinates)
            """,
            image_id=image_id, vector_id=vector.id, length=vector.length, angle=angle, x1=vector.x1, y1=vector.y1,
            x2=vector.x2, y2=vector.y2)


def save_intersection_data(tx: ManagedTransaction,
                           image_id: str,
                           angle_points: List[AnglePoint]):
    query: str = """
            UNWIND $angle_points AS data
            
            // Create or match AnglePointCoordinates node
            MERGE (apCoords:AnglePointCoordinates:Feature {x: data.x, y: data.y})
            ON CREATE SET apCoords.samples = [$image_id]
            ON MATCH SET apCoords.samples = CASE WHEN $image_id IN apCoords.samples THEN apCoords.samples ELSE apCoords.samples + $image_id END
            
            // Create or match AnglePointAngle node
            MERGE (apAngle:AnglePointAngle:Feature {angle: data.angle})
            ON CREATE SET apAngle.samples = [$image_id]
            ON MATCH SET apAngle.samples = CASE WHEN $image_id IN apAngle.samples THEN apAngle.samples ELSE apAngle.samples + $image_id END
            
            MERGE (ap:AnglePoint)-[:HAS_ANGLE]->(apAngle)
        
            ON CREATE SET ap.id = data.id, ap.image_id = $image_id, ap.samples = [$image_id]
            ON MATCH SET ap.id = data.id, ap.image_id = $image_id, ap.samples = ap.samples + $image_id
            
            MERGE (ap)-[:HAS_COORDINATES]->(apCoords)

            WITH ap, data
            MATCH (vector1:Vector {vector_id: data.line1})
            MATCH (vector2:Vector {vector_id: data.line2})
            MERGE (vector1)-[:HAS_ANGLE_POINT]->(ap)
            MERGE (vector2)-[:HAS_ANGLE_POINT]->(ap)
        """
    points_ = [vars(angle_point) for angle_point in angle_points]
    logging.info(f"Saving intersection data for image {image_id} with {points_} angle points")
    tx.run(query, angle_points=points_, image_id=image_id)


def calculate_abs_angle(x1, y1, x2, y2):
    angle_radians = math.atan2(y2 - y1, x2 - x1)
    angle_degrees = math.degrees(angle_radians)
    return round_to_nearest(abs(angle_degrees), 5)


def round_to_nearest(number, n):
    return round(number / n) * n
