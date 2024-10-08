import logging
import math
from typing import List

from neo4j import ManagedTransaction

from model.point import IntersectionPoint, EndPoint, Point
from model.vector_details import VectorDetails


def save_vectors_data(tx, vectors: List[VectorDetails], image_id: str, session_id: str):
    for vector in vectors:
        angle = calculate_abs_angle(vector.x1, vector.y1, vector.x2, vector.y2)
        tx.run(
            """
            // Create or match Length node
            MERGE (length:Length:Feature {value: $length, session_id: $session_id})
            ON CREATE SET length.samples = [$image_id]
            ON MATCH SET length.samples = CASE WHEN $image_id IN length.samples THEN length.samples ELSE length.samples + $image_id END
            
            // Create or match Angle node
            MERGE (angle:Angle:Feature {value: $angle, session_id: $session_id})
            ON CREATE SET angle.samples = [$image_id]
            ON MATCH SET angle.samples = CASE WHEN $image_id IN angle.samples THEN angle.samples ELSE angle.samples + $image_id END
            
            // Create or match Coordinates node
            MERGE (coordinates:Coordinates:Feature {x1: $x1, y1: $y1, x2: $x2, y2: $y2, session_id: $session_id})
            ON CREATE SET coordinates.samples = [$image_id]
            ON MATCH SET coordinates.samples = CASE WHEN $image_id IN coordinates.samples THEN coordinates.samples ELSE coordinates.samples + $image_id END
            
            // Always create a new Vector node
            CREATE (v:Vector {image_id: $image_id, vector_id: $vector_id, samples: [$image_id], session_id: $session_id})
            CREATE (v)-[:HAS_ANGLE]->(angle)
            CREATE (v)-[:HAS_LENGTH]->(length)
            CREATE (v)-[:HAS_COORDINATES]->(coordinates)
            """,
            image_id=image_id,
            vector_id=vector.id,
            length=vector.length,
            angle=angle,
            x1=vector.x1,
            y1=vector.y1,
            x2=vector.x2,
            y2=vector.y2,
            session_id=session_id,
        )


def save_intersection_data(
    tx: ManagedTransaction, image_id: str, intersection_points: List[IntersectionPoint], session_id: str
):
    query: str = """
            UNWIND $angle_points AS data
            
            // Create or match PointCoordinates node
            MERGE (pointCoords:PointCoordinates:Feature {x: data.x, y: data.y, session_id: $session_id})
            ON CREATE SET pointCoords.samples = [$image_id]
            ON MATCH SET pointCoords.samples = CASE WHEN $image_id IN pointCoords.samples THEN pointCoords.samples ELSE pointCoords.samples + $image_id END
            
            // Create or match IntersectionPointAngle node
            MERGE (ipAngle:IntersectionPointAngle:Feature {angle: data.angle, session_id: $session_id})
            ON CREATE SET ipAngle.samples = [$image_id]
            ON MATCH SET ipAngle.samples = CASE WHEN $image_id IN ipAngle.samples THEN ipAngle.samples ELSE ipAngle.samples + $image_id END
            
            CREATE (point:IntersectionPoint {session_id: $session_id, id: data.id, image_id: $image_id, samples: [$image_id]})-[:HAS_ANGLE]->(ipAngle)
            
            MERGE (point)-[:HAS_COORDINATES]->(pointCoords)

            WITH point, data
            MATCH (vector1:Vector {vector_id: data.line1, session_id: $session_id})
            MATCH (vector2:Vector {vector_id: data.line2, session_id: $session_id})
            MERGE (vector1)-[:HAS_ANGLE_POINT]->(point)
            MERGE (vector2)-[:HAS_ANGLE_POINT]->(point)
        """
    points_ = [vars(intersection_point) for intersection_point in intersection_points]
    logging.info(
        f"Saving intersection data for image {image_id} with {len(points_)} points"
    )
    tx.run(query, angle_points=points_, image_id=image_id, session_id=session_id)

def save_points_data(tx: ManagedTransaction, points: List[EndPoint], image_id: str, session_id: str):
    for point in points:
        tx.run(
            """
                CREATE (p:EndPoint {id: $id, session_id: $session_id, samples: [$image_id]})-[:HAS_COORDINATES]->(pCoords:PointCoordinates:Feature {x: $x, y: $y, session_id: $session_id, samples: [$image_id]})
                WITH p
                MATCH (vector1:Vector {vector_id: $line, session_id: $session_id})
                MERGE (vector1)-[:HAS_POINT]->(p)
            """,
            id=point.id,
            x=point.x,
            y=point.y,
            session_id=session_id,
            line=point.line,
            image_id=image_id,
        )

def calculate_abs_angle(x1, y1, x2, y2):
    angle_radians = math.atan2(y2 - y1, x2 - x1)
    angle_degrees = math.degrees(angle_radians)
    return round_to_nearest(abs(angle_degrees), 5)


def round_to_nearest(number, n):
    return round(number / n) * n
