import logging
from typing import List
from neo4j import GraphDatabase, ManagedTransaction, Session
import networkx as nx
from neo4j_to_networkx import Neo4jToNetworkx
import json

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

    def _save_concept(self, tx: ManagedTransaction, concept_id: str, graph: nx.Graph) -> None:
        """Save a NetworkX graph to the Neo4j database.

        Args:
            graph: A NetworkX graph object (Graph, DiGraph, MultiGraph, or MultiDiGraph).

        Raises:
            ValueError: If an edge is missing a 'label' attribute.
        """
    
        # Helper functions for serialization
        def is_primitive(value):
            return isinstance(value, (int, float, str, bool, type(None)))

        def is_list_of_primitives(value):
            return isinstance(value, list) and all(is_primitive(item) for item in value)

        def needs_serialization(value):
            if is_primitive(value):
                return False
            elif isinstance(value, list):
                return not is_list_of_primitives(value)
            else:
                return True

        def serialize_value(value):
            if needs_serialization(value):
                return json.dumps(value)
            else:
                return value

        # Step 1: Create nodes and map NetworkX node IDs to Neo4j node IDs
        node_mapping = {}
        for node in graph.nodes:
            # Get node data (attributes)
            node_data = graph.nodes[node]
            # Extract labels from the 'labels' property, defaulting to an empty list
            labels = node_data.get('labels', [])
            # Ensure labels is a list (convert single label to list if needed)
            if not isinstance(labels, list):
                labels = [labels]
            # Build the labels string for Cypher (e.g., ":Label1:Label2")
            labels_str = ':' + ':'.join(labels) if labels else ''
            # Collect other properties, excluding 'labels', and serialize non-primitive values
            properties = {k: serialize_value(v) for k, v in node_data.items() if k != 'labels'}
            properties["concept_id"] = concept_id
            # Create the node in Neo4j and retrieve its internal ID
            query = f"CREATE (n{labels_str} $properties) RETURN id(n) as node_id"
            result = tx.run(query, properties=properties)
            record = result.single()
            neo4j_id = record["node_id"]
            node_mapping[node] = neo4j_id

        # Step 2: Create relationships based on edge labels
        for u, v, data in graph.edges(data=True):
            # Get the Neo4j node IDs for the start and end nodes
            start_id = node_mapping[u]
            end_id = node_mapping[v]
            # Create a directed relationship with the edge label as the type
            query = (
                "MATCH (a), (b) "
                "WHERE id(a) = $start_id AND id(b) = $end_id "
                "CREATE (a)-[:CONNECTED_TO]->(b)"
            )
            tx.run(query, start_id=start_id, end_id=end_id)

    def _remove_image_data(self, tx: ManagedTransaction, image_id: str) -> None:
        """Remove all data for an image."""
        # First remove relationships
        query = """
        MATCH (n)
        WHERE n.image_id = $image_id OR $image_id IN n.samples
        DETACH DELETE n
        """
        tx.run(query, image_id=image_id)
