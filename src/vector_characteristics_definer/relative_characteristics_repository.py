import logging

from neo4j import GraphDatabase


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

    def create_relative_characteristics(self):
        logging.info("Creating relative characteristics")
        with self.driver.session() as session:
            session.write_transaction(self._create_relative_characteristics)
            logging.debug("Transaction for _create_relative_characteristics completed")

    @staticmethod
    def _create_relative_characteristics(tx):
        logging.debug("Running _create_relative_characteristics transaction")
        query = """
            MATCH (coord:Coordinates)--(:Location)--(line:Line)-[:INCLUDES]->(ap1:AnglePoint)--(apLoc1:AnglePointLocation),
                (line)-[:INCLUDES]->(ap2:AnglePoint)--(apLoc2:AnglePointLocation),
                (angle:Angle)--(:Orientation)--(line)
            WHERE apLoc1.x <> apLoc2.x AND apLoc1.y <> apLoc2.y
            MERGE (v:Vector {line_id: line.id})
            ON CREATE SET v.vector_id = randomUUID()
            MERGE (line)-[:INCLUDES]->(v)
            MERGE (v)-[:INCLUDES]->(ap1)
            MERGE (v)-[:INCLUDES]->(ap2)
            MERGE (v)-[:HAS]->(vLocation:VectorLocation {vector_id: v.vector_id})
            MERGE (vOrient:VectorOrientation {vector_id: v.vector_id})<-[:HAS]-(v)
            MERGE (vAngle:VectorAngle {value: angle.value, vector_id: v.vector_id})<-[:HAS]-(vOrient)
            WITH v, vLocation, apLoc1, apLoc2
            MERGE (vLocation)-[:HAS]->(vCoordinates:VectorCoordinates {vector_id: v.vector_id})
            ON CREATE SET vCoordinates.x1 = apLoc1.x, vCoordinates.y1 = apLoc1.y, vCoordinates.x2 = apLoc2.x, vCoordinates.y2 = apLoc2.y
            WITH v, apLoc1, apLoc2
            MATCH (v)-[:HAS]->(vLocation:VectorLocation)-[:HAS]->(vCoordinates:VectorCoordinates)
            WITH v, vCoordinates, sqrt((vCoordinates.x2 - vCoordinates.x1) * (vCoordinates.x2 - vCoordinates.x1) + (vCoordinates.y2 - vCoordinates.y1) * (vCoordinates.y2 - vCoordinates.y1)) AS magnitude
            MERGE (vectorLength:VectorLength {vector_id: v.vector_id})<-[:HAS]-(v)
            MERGE (vectorMagnitude:VectorMagnitude {value: magnitude, vector_id: v.vector_id})<-[:HAS]-(vectorLength)
        """
        logging.debug(f"Running query: {query}")
        tx.run(query)
