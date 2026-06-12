import logging
from typing import List
from neo4j import GraphDatabase, ManagedTransaction
import networkx as nx
from src.neo4j_to_networkx import Neo4jToNetworkx
from src.networkx_to_neo4j import NetworkxToNeo4j


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

    def get_image_graph(self, image_id: str) -> nx.Graph:
        with self.driver.session() as session:
            return Neo4jToNetworkx.extract_image_graph(session, image_id)

    def get_image_ids_for_session(self, session_id: str) -> List[str]:
        """
        Get all image IDs for a session.

        Args:
            session_id: The session ID to look up

        Returns:
            List of image IDs for the session
        """
        logging.info(f"Getting image IDs for session {session_id}")
        with self.driver.session() as session:
            return session.execute_read(self._get_image_ids_for_session, session_id)

    def save_concept(self, concept_id: str, concept_graph: nx.Graph) -> None:
        """
        Save a concept to the database.

        Args:
            concept_id: The concept ID to save
            neo4j_data: List of dictionaries representing nodes and relationships
        """
        logging.info(f"Saving concept {concept_id}")
        with self.driver.session() as session:
            session.execute_write(self._save_concept, concept_id, concept_graph)

    def remove_image_data(self, image_id: str) -> None:
        """
        Remove all data for an image.

        Args:
            image_id: The image ID to remove
        """
        logging.info(f"Removing data for image {image_id}")
        with self.driver.session() as session:
            session.execute_write(self._remove_image_data, image_id)

    def _get_image_ids_for_session(
        self, tx: ManagedTransaction, session_id: str
    ) -> List[str]:
        """Get all image IDs for a session."""
        query = """
            MATCH (n {session_id: $session_id})
            RETURN DISTINCT n.image_id AS image_id
        """
        result = tx.run(query, session_id=session_id)
        return [
            record["image_id"] for record in result if record["image_id"] is not None
        ]

    def _get_nodes_and_edges_for_image(
        self, tx: ManagedTransaction, image_id: str
    ) -> List[dict]:
        """Get all nodes and edges for an image."""
        query = """
        MATCH (n {image_id: $image_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) as node_labels, properties(n) as node_properties
        OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
        WITH n, node_labels, node_properties, r, m
        RETURN id(n) as node_id, 
               node_labels, 
               type(r) as rel_type, 
               id(m) as target_id,
               node_properties
        """
        result = tx.run(query, image_id=image_id)
        return [record.data() for record in result]

    def _save_concept(
        self, tx: ManagedTransaction, concept_id: str, graph: nx.Graph
    ) -> None:
        """Save a NetworkX graph to the Neo4j database in a single transaction.

        Args:
            graph: A NetworkX graph object (Graph, DiGraph, MultiGraph, or MultiDiGraph).
        """
        NetworkxToNeo4j.create_structure(tx, graph, concept_id)

    def _remove_image_data(self, tx: ManagedTransaction, image_id: str) -> None:
        """Remove all data for an image."""
        # First remove relationships
        query = """
        MATCH (n)
        WHERE n.image_id = $image_id OR $image_id IN n.samples
        DETACH DELETE n
        """
        tx.run(query, image_id=image_id)
