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
            CALL {
                MATCH (n {session_id: $session_id})
                WHERE n:Vector OR n:AnglePoint OR n:Feature
                RETURN max(size(n.samples)) AS maxSamples
            }
            CALL {
                MATCH (apc:AnglePointsCount:Feature {session_id: $session_id})
                RETURN min(apc.count) AS minAnglePoints
            }
            CALL {
                MATCH (vc:VectorsCount:Feature {session_id: $session_id})
                RETURN min(vc.count) AS minVectors
            }
            WITH maxSamples, minAnglePoints, minVectors
            MATCH (n {session_id: $session_id})
            WHERE (n:Vector OR n:AnglePoint OR n:Feature OR n:EndPoint)
                AND (
                    (n:AnglePointsCount AND n.count > minAnglePoints)
                    OR (n:VectorsCount AND n.count > minVectors)
                    OR (NOT n:AnglePointsCount AND NOT n:VectorsCount AND size(n.samples) < maxSamples)
                )
            DETACH DELETE n
            RETURN maxSamples, minAnglePoints, minVectors
        """
        result = tx.run(query, session_id=session_id)
        return [dict(record) for record in result]