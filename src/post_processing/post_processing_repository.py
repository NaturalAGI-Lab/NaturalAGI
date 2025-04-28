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

    def find_stable_structures(self, tx: ManagedTransaction, session_id: str):
        query = """
        // Find the most common structure by counting occurrences of similar node and segment counts
        MATCH (n {session_id: $session_id})
        WHERE n:Vector OR n:Point
        WITH n.image_id AS image_id, n
        OPTIONAL MATCH (n)-[:HAS_RELATIVE_POSITION]->(s:Segment)
        WITH image_id, COUNT(DISTINCT n) AS node_count, COUNT(DISTINCT s) AS segment_count
        WITH node_count, segment_count, COUNT(*) as frequency, COLLECT(image_id) as image_ids
        ORDER BY frequency DESC
        LIMIT 1
        WITH image_ids[0] as image_id, node_count, segment_count

        // Find max samples and min counts for all features before any deletions
        MATCH (count_node {session_id: $session_id})
        WHERE count_node:EndPointsCount OR count_node:IntersectionPointsCount 
           OR count_node:VectorsCount OR count_node:CornerPointsCount 
           OR count_node:CycleCount OR count_node:QuadrantChangeCount
           OR count_node:GraphDensity OR count_node:AverageClusteringCoefficient
           OR count_node:AveragePathLength OR count_node:GraphDiameter
           OR count_node:GraphRadius OR count_node:AverageDegree
           OR count_node:AverageBetweenness OR count_node:AverageCloseness
        WITH image_id, node_count, segment_count,
             max(size(count_node.samples)) AS maxSamples,
             min(CASE WHEN count_node:EndPointsCount THEN count_node.value ELSE null END) AS minEndPoints,
             min(CASE WHEN count_node:IntersectionPointsCount THEN count_node.value ELSE null END) AS minIntersectionPoints,
             min(CASE WHEN count_node:VectorsCount THEN count_node.value ELSE null END) AS minVectors,
             min(CASE WHEN count_node:CornerPointsCount THEN count_node.value ELSE null END) AS minCornerPoints,
             min(CASE WHEN count_node:CycleCount THEN count_node.value ELSE null END) AS minCycleCount,
             min(CASE WHEN count_node:QuadrantChangeCount THEN count_node.value ELSE null END) AS minQuadrantChangeCount,
             min(CASE WHEN count_node:GraphDensity THEN count_node.value ELSE null END) AS minGraphDensity,
             min(CASE WHEN count_node:AverageClusteringCoefficient THEN count_node.value ELSE null END) AS minClusteringCoeff,
             min(CASE WHEN count_node:AveragePathLength THEN count_node.value ELSE null END) AS minPathLength,
             min(CASE WHEN count_node:GraphDiameter THEN count_node.value ELSE null END) AS minDiameter,
             min(CASE WHEN count_node:GraphRadius THEN count_node.value ELSE null END) AS minRadius,
             min(CASE WHEN count_node:AverageDegree THEN count_node.value ELSE null END) AS minAvgDegree,
             min(CASE WHEN count_node:AverageBetweenness THEN count_node.value ELSE null END) AS minAvgBetweenness,
             min(CASE WHEN count_node:AverageCloseness THEN count_node.value ELSE null END) AS minAvgCloseness

        // First, remove relationships except HAS_RELATIVE_POSITION
        CALL {
            WITH image_id
            MATCH (n {session_id: $session_id})-[r]-(m:Feature)
            DELETE r
        }

        // Then delete structural nodes and their segments that are not from the sample with the most common structure
        CALL {
            WITH image_id
            MATCH (n {session_id: $session_id})
            WHERE (n:Vector OR n:Point) AND n.image_id <> image_id
            OPTIONAL MATCH (n)-[:HAS_RELATIVE_POSITION]->(s:Segment)
            DETACH DELETE n, s
        }

        // Finally delete feature nodes that don't meet criteria
        CALL {
            WITH maxSamples, minEndPoints, minVectors, minIntersectionPoints, 
                 minCornerPoints, minCycleCount, minQuadrantChangeCount,
                 minGraphDensity, minClusteringCoeff, minPathLength, minDiameter,
                 minRadius, minAvgDegree, minAvgBetweenness, minAvgCloseness
            MATCH (n {session_id: $session_id})
            WHERE (n:EndPointsCount AND n.value > minEndPoints)
               OR (n:VectorsCount AND n.value > minVectors)
               OR (n:IntersectionPointsCount AND n.value > minIntersectionPoints)
               OR (n:CornerPointsCount AND n.value > minCornerPoints)
               OR (n:CycleCount AND n.value > minCycleCount)
               OR (n:QuadrantChangeCount AND n.value > minQuadrantChangeCount)
               OR (n:GraphDensity AND n.value > minGraphDensity)
               OR (n:AverageClusteringCoefficient AND n.value > minClusteringCoeff)
               OR (n:AveragePathLength AND n.value > minPathLength)
               OR (n:GraphDiameter AND n.value > minDiameter)
               OR (n:GraphRadius AND n.value > minRadius)
               OR (n:AverageDegree AND n.value > minAvgDegree)
               OR (n:AverageBetweenness AND n.value > minAvgBetweenness)
               OR (n:AverageCloseness AND n.value > minAvgCloseness)
               OR (n:Feature 
                   AND NOT (n:EndPointsCount OR n:VectorsCount OR n:IntersectionPointsCount 
                        OR n:CornerPointsCount OR n:CycleCount OR n:QuadrantChangeCount
                        OR n:GraphDensity OR n:AverageClusteringCoefficient OR n:AveragePathLength 
                        OR n:GraphDiameter OR n:GraphRadius OR n:AverageDegree 
                        OR n:AverageBetweenness OR n:AverageCloseness) 
                   AND size(n.samples) < maxSamples)
                AND NOT n:Segment  // Explicitly prevent deletion of Segment nodes
            DETACH DELETE n
        }
        """
        tx.run(query, session_id=session_id)
