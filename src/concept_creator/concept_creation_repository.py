import logging
import hashlib
from typing import List
from neo4j import GraphDatabase, ManagedTransaction

from feature_weight_service import FeatureWeightService


class ConceptCreationRepository:
    def __init__(self, uri: str, user: str, password: str):
        logging.info("Initializing ConceptCreationRepository")
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

    def create_concept(self, session_id: str, concept_name: str) -> str:
        logging.info("Starting create_concept method")
        with self.driver.session() as session:
            concept_id = session.execute_write(
                self._create_concept, session_id, concept_name
            )
            logging.info(f"Concept created with id: {concept_id}")
            session.execute_write(FeatureWeightService().calculate_feature_weights)
        return concept_id

    def _create_concept(
        self, tx: ManagedTransaction, session_id: str, concept_name: str
    ) -> str:
        # Fetch all nodes for the session
        query = """
            MATCH (n {session_id: $session_id})
            WHERE NOT n:Concept
            RETURN collect(n) AS nodes, count(n) AS node_count
        """
        result = tx.run(query, session_id=session_id)
        data = result.single()
        nodes = data["nodes"]
        node_count = data["node_count"]

        if node_count == 0:
            raise ValueError(f"No nodes found for session {session_id}")

        # Generate hash from node properties
        concept_id = self._generate_concept_hash(nodes)

        # Check if concept with this hash already exists
        if self._concept_exists(tx, concept_id):
            self._remove_session_nodes(tx, session_id)
            error_message = f"Concept with id {concept_id} already exists. All nodes for session {session_id} have been removed."
            logging.error(error_message)
            return concept_id

        # Create Concept node and link session nodes to it
        self._create_concept_node(tx, concept_id, session_id, nodes, concept_name)

        return concept_id

    def _generate_concept_hash(self, nodes: List[dict]) -> str:
        hasher = hashlib.sha256()

        # Sort nodes by their labels to ensure consistent ordering
        sorted_nodes = sorted(nodes, key=lambda n: ",".join(sorted(n.labels)))

        for node in sorted_nodes:
            node_info = []

            # Add labels
            node_info.append(",".join(sorted(node.labels)))

            # Add counts for specific features
            if "VectorsCount" in node.labels:
                node_info.append(f"VectorsCount:{node['count']}")
            if "IntersectionPointsCount" in node.labels:
                node_info.append(f"IntersectionPointsCount:{node['count']}")
            if "CornerPointsCount" in node.labels:
                node_info.append(f"CornerPointsCount:{node['count']}")
            if "EndPointsCount" in node.labels:
                node_info.append(f"EndPointsCount:{node['count']}")

            # Add specific feature values
            if "ContourType" in node.labels:
                node_info.append(f"ContourType:{node['value']}")

            # Create a string representation of the node info and update the hasher
            node_str = "|".join(node_info)
            hasher.update(node_str.encode())

        return hasher.hexdigest()

    def _concept_exists(self, tx: ManagedTransaction, concept_id: str) -> bool:
        query = """
            MATCH (c:Concept {id: $concept_id})
            RETURN count(c) > 0 AS exists
        """
        result = tx.run(query, concept_id=concept_id)
        return result.single()["exists"]

    def _remove_session_nodes(self, tx: ManagedTransaction, session_id: str):
        query = """
            MATCH (n {session_id: $session_id})
            DETACH DELETE n
        """
        tx.run(query, session_id=session_id)

    def _create_concept_node(
        self,
        tx: ManagedTransaction,
        concept_id: str,
        session_id: str,
        nodes: List[dict],
        concept_name: str,
    ):
        node_data = [{"id": node.id, "labels": list(node.labels)} for node in nodes]

        query = """
            MATCH (f:Feature {session_id: $session_id})
            WITH max(size(f.samples)) AS samples_count
            CREATE (c:Concept {
                id: $concept_id, 
                session_id: $session_id, 
                name: $concept_name, 
                samples_count: samples_count
            })
            WITH c
            UNWIND $node_data AS node
            MATCH (n) WHERE id(n) = node.id
            CREATE (c)-[:INCLUDES]->(n)
            SET n.concept_id = $concept_id
            RETURN c
        """

        result = tx.run(
            query,
            concept_id=concept_id,
            session_id=session_id,
            node_data=node_data,
            concept_name=concept_name,
        )
        return result.single()["c"]
