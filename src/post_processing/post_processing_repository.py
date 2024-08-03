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

    def stabilize_structures(self) -> List[Dict[str, Any]]:
        logging.info("Starting stabilize_structures method")
        with self.driver.session() as session:
            return session.write_transaction(self.find_stable_structures)

    def find_stable_structures(self, tx: ManagedTransaction) -> List[Dict[str, Any]]:
        query = """
            CALL {
                MATCH (n)
                WHERE n:Vector OR n:AnglePoint OR n:Feature
                RETURN max(size(n.samples)) AS maxSamples
            }
            WITH maxSamples
            MATCH (n)
            WHERE (n:Vector OR n:AnglePoint OR n:Feature)
                AND size(n.samples) < maxSamples
            DETACH DELETE n
        """
        result = tx.run(query)
        return [dict(record) for record in result]