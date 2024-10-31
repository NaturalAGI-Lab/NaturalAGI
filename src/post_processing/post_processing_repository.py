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
        // Find the sample with the least amount of structural nodes
        MATCH (n {session_id: $session_id})
        WHERE n:Vector OR n:Point
        WITH n.image_id AS image_id, COUNT(n) AS node_count
        ORDER BY node_count ASC
        LIMIT 1
        
        // TODO: think how to utilize the link between Features and Structural Nodes
        // Remove relations from Features to Structural Nodes
        CALL {
            WITH image_id
            MATCH (n {session_id: $session_id})-[r]-(m:Feature)
            DELETE r
        }

        // Keep structural nodes from the sample with the least nodes
        MATCH (structural_node {session_id: $session_id, image_id: image_id})
        WHERE structural_node:Vector OR structural_node:Point
        
        // Find max samples and min counts for *Count features
        MATCH (count_node {session_id: $session_id})
        WHERE count_node:EndPointsCount OR count_node:IntersectionPointsCount OR count_node:VectorsCount OR count_node:CornerPointsCount
        WITH structural_node, image_id,
             max(size(count_node.samples)) AS maxSamples,
             min(CASE WHEN count_node:EndPointsCount THEN count_node.count ELSE null END) AS minEndPoints,
             min(CASE WHEN count_node:IntersectionPointsCount THEN count_node.count ELSE null END) AS minIntersectionPoints,
             min(CASE WHEN count_node:VectorsCount THEN count_node.count ELSE null END) AS minVectors,
             min(CASE WHEN count_node:CornerPointsCount THEN count_node.count ELSE null END) AS minCornerPoints

        // Delete structural nodes that are not from the sample with the least nodes
        CALL {
            WITH image_id
            MATCH (n {session_id: $session_id})
            WHERE (n:Vector OR n:Point) AND n.image_id <> image_id
            DETACH DELETE n
        }

        // Delete *Count nodes that don't meet the criteria
        CALL {
            WITH maxSamples, minEndPoints, minVectors, minIntersectionPoints, minCornerPoints
            MATCH (n {session_id: $session_id})
            WHERE (n:EndPointsCount AND n.count > minEndPoints)
               OR (n:VectorsCount AND n.count > minVectors)
               OR (n:IntersectionPointsCount AND n.count > minIntersectionPoints)
               OR (n:CornerPointsCount AND n.count > minCornerPoints)
               OR (n:Feature AND NOT (n:EndPointsCount OR n:VectorsCount OR n:IntersectionPointsCount OR n:CornerPointsCount) AND size(n.samples) < maxSamples)
            DETACH DELETE n
        }

        RETURN image_id, maxSamples, minEndPoints, minVectors, minIntersectionPoints, minCornerPoints
        """
        result = tx.run(query, session_id=session_id)
        logging.info(f"Result: {result}")
        return [dict(record) for record in result]
