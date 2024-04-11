import logging

from neo4j import GraphDatabase
import numpy as np

logging.basicConfig(level=logging.INFO)

class VectorCharacteristicsRepository:
    def __init__(self, uri, user, password):
        logging.info("Initializing VectorCharacteristicsRepository")
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logging.info("Database connection established")

        except Exception as e:
            logging.error(f"Error establishing database connection: {e}")
            raise

    def close(self):
        try:
            self.driver.close()
            logging.info("Database connection closed")
        except Exception as e:
            logging.error(f"Error closing database connection: {e}")
            raise

    def create_relative_characteristics(self, image_id):
        logging.info("Creating relative characteristics")
        with self.driver.session() as session:
            session.write_transaction(self._create_relative_characteristics, image_id)
            line_endpoints = session.read_transaction(self._retrieve_line_endpoints, image_id)
            for data in line_endpoints:
                angle = self.calculate_angle(*data["coordinates"])
                session.write_transaction(self._update_angle, data["line1_id"], data["line2_id"], angle)
            logging.debug("Transaction for _create_relative_characteristics completed")

    @staticmethod
    def _create_relative_characteristics(tx, image_id):
        logging.debug("Running _create_relative_characteristics transaction")
        query = """
            MATCH (coord:Coordinates)--(:Location)--(line:Line {image_id: $image_id})-[:HAS_ANGLE_POINT]->(ap1:AnglePoint)--(apLoc1:AnglePointCoordinates),
                (line)-[:HAS_ANGLE_POINT]->(ap2:AnglePoint)--(apLoc2:AnglePointCoordinates),
                (angle:Angle)--(:Orientation)--(line)
            WHERE apLoc1.x <> apLoc2.x OR apLoc1.y <> apLoc2.y
            MERGE (v:Vector {line_id: line.id, image_id: $image_id})
            ON CREATE SET v.vector_id = randomUUID()
            MERGE (line)-[:IS_VECTOR]->(v)
            MERGE (v)-[:HAS_ANGLE_POINT]->(ap1)
            MERGE (v)-[:HAS_ANGLE_POINT]->(ap2)
            MERGE (vAngle:VectorAngle {value: angle.value})
            MERGE (vAngle)<-[:HAS_VECTOR_ANGLE]-(v)
            WITH v, apLoc1, apLoc2
            MERGE (vCoordinates:VectorCoordinates {x1: apLoc1.x, y1: apLoc1.y, x2: apLoc2.x, y2: apLoc2.y})
            MERGE (v)-[:HAS_VECTOR_COORDINATES]->(vCoordinates)
            WITH v, vCoordinates, sqrt((vCoordinates.x2 - vCoordinates.x1) * (vCoordinates.x2 - vCoordinates.x1) + (vCoordinates.y2 - vCoordinates.y1) * (vCoordinates.y2 - vCoordinates.y1)) AS magnitude
            MERGE (vectorMagnitude:VectorMagnitude {value: magnitude})
            MERGE (vectorMagnitude)<-[:HAS_MAGNITUDE]-(v)
        """
        logging.debug(f"Running query: {query}")
        tx.run(query, image_id=image_id)
    
    @staticmethod
    def _update_angle(tx, vector1_id, vector2_id, angle):
        query = """
            MATCH (v1:Vector {id: $vector1_id})-[:HAS_ANGLE_POINT]->(ap:AnglePoint)<-[:HAS_ANGLE_POINT]-(v2:Vector {id: $vector2_id})
            MATCH (ap)-[:HAS_ANGLE]->(apLoc:AnglePointAngle)
            SET apLoc.angle = $angle
        """
        tx.run(query, vector1_id=vector1_id, vector2_id=vector2_id, angle=angle)
    
    @staticmethod
    def _retrieve_line_endpoints(tx, image_id):
        query = """
            MATCH (l1:Line {image_id: $image_id})-[:HAS_LOCATION]->(:Location)-[:HAS_COORDINATES]->(coord1:Coordinates),
                (l2:Line {image_id: $image_id})-[:HAS_LOCATION]->(:Location)-[:HAS_COORDINATES]->(coord2:Coordinates)
            WHERE l1 <> l2
            RETURN l1.id AS line1_id, coord1.x1 AS x1, coord1.y1 AS y1, coord1.x2 AS x2, coord1.y2 AS y2,
                l2.id AS line2_id, coord2.x1 AS x3, coord2.y1 AS y3, coord2.x2 AS x4, coord2.y2 AS y4
        """
        results = []
        for record in tx.run(query, image_id=image_id):
            results.append({
                "line1_id": record["line1_id"],
                "line2_id": record["line2_id"],
                "coordinates": [record["x1"], record["y1"], record["x2"], record["y2"], record["x3"], record["y3"], record["x4"], record["y4"]]
            })
        return results
    
    @staticmethod
    def calculate_angle(x1, y1, x2, y2, x3, y3, x4, y4):
        """
        Calculate the angle between two lines given their endpoints.

        Args:
        x1, y1: Coordinates of the first point of the first line.
        x2, y2: Coordinates of the second point of the first line.
        x3, y3: Coordinates of the first point of the second line.
        x4, y4: Coordinates of the second point of the second line.

        Returns:
        angle: The angle between the two lines in degrees.
        """

        # Convert points to vectors
        vector1 = np.array([x2 - x1, y2 - y1])
        vector2 = np.array([x4 - x3, y4 - y3])

        # Calculate the dot product
        dot_product = np.dot(vector1, vector2)

        # Calculate the magnitudes of the vectors
        magnitude_v1 = np.linalg.norm(vector1)
        magnitude_v2 = np.linalg.norm(vector2)

        # Avoid division by zero
        if magnitude_v1 == 0 or magnitude_v2 == 0:
            return 0

        # Calculate the cosine of the angle
        cos_angle = dot_product / (magnitude_v1 * magnitude_v2)

        # Make sure the cosine value is in the range [-1, 1] to avoid NaN results
        cos_angle = max(min(cos_angle, 1), -1)

        # Calculate the angle in radians and then convert to degrees
        angle = np.degrees(np.arccos(cos_angle))

        return angle