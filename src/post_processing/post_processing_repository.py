import logging
from typing import Any, Dict, List

from neo4j import GraphDatabase, ManagedTransaction

logging.basicConfig(level=logging.DEBUG)


class PostProcessingRepository:

    def __init__(self, uri, user, password):
        logging.info("Initializing Neo4jConnection")
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

    def merge_nodes_location(self, node_labels: list[str]):
        logging.info("Starting merge_vector_location method")
        with self.driver.session() as session:
            for node_label in node_labels:
                session.write_transaction(self._merge_node_transaction, node_label)

    def stabilize_structures(self, session_id: str) -> List[Dict[str, Any]]:
        logging.info("Starting stabilize_structures method")
        with self.driver.session() as session:
            return session.write_transaction(self.find_stable_structures, session_id)

    def find_stable_structures(self, tx: ManagedTransaction, session_id: str) -> List[Dict[str, Any]]:
        query = """
        // Find max samples and min counts
        MATCH (n {session_id: $session_id})
        WHERE n:Vector OR n:Point OR n:Feature
        WITH max(size(n.samples)) AS maxSamples,
             min(CASE WHEN n:EndPointsCount THEN n.count ELSE null END) AS minEndPoints,
             min(CASE WHEN n:IntersectionPointsCount THEN n.count ELSE null END) AS minIntersectionPoints,
             min(CASE WHEN n:VectorsCount THEN n.count ELSE null END) AS minVectors

        // Delete nodes that don't meet the criteria
        CALL {
            MATCH (n {session_id: $session_id})
            WHERE n:Vector OR n:Point
            DETACH DELETE n
        }
        CALL {
            WITH maxSamples
            MATCH (n:Feature {session_id: $session_id})
            WHERE size(n.samples) < maxSamples
            DETACH DELETE n
        }
        CALL {
            WITH minEndPoints, minVectors, minIntersectionPoints
            MATCH (n {session_id: $session_id})
            WHERE (n:EndPointsCount AND n.count > minEndPoints)
               OR (n:VectorsCount AND n.count > minVectors)
               OR (n:IntersectionPointsCount AND n.count > minIntersectionPoints)
            DETACH DELETE n
        }
        RETURN maxSamples, minEndPoints, minVectors, minIntersectionPoints
        """
        result = tx.run(query, session_id=session_id)
        logging.info(f"Result: {result}")
        return [dict(record) for record in result]
