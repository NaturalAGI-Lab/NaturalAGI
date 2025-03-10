import logging
from typing import Dict, List, Any
import networkx as nx
from neo4j import Session

logging.basicConfig(level=logging.INFO)


class Neo4jToNetworkx:
    """Responsible for converting Neo4j graphs to NetworkX format"""

    @staticmethod
    def extract_image_graph(session: Session, image_id: str) -> nx.Graph:
        """Extract graph from Neo4j and convert to NetworkX format."""
        query = """
        MATCH (n {image_id: $image_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) as node_labels
        OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
        WITH n, node_labels, r, m
        RETURN id(n) as node_id, 
               node_labels, 
               type(r) as rel_type, 
               id(m) as target_id
        """
        result = session.run(query, image_id=image_id)
        return Neo4jToNetworkx._build_networkx_graph(result)

    @staticmethod
    def extract_concept_graph(session: Session, concept_id: str) -> nx.Graph:
        """Extract graph from Neo4j and convert to NetworkX format."""
        query = """
        MATCH (n {concept_id: $concept_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) as node_labels
        OPTIONAL MATCH (n)-[r]-(m {concept_id: $concept_id})
        WITH n, node_labels, r, m
        RETURN id(n) as node_id, 
               node_labels, 
               type(r) as rel_type, 
               id(m) as target_id
        """
        result = session.run(query, concept_id=concept_id)
        return Neo4jToNetworkx._build_networkx_graph(result)

    @staticmethod
    def convert(nodes_and_edges: List[Dict[str, Any]]) -> nx.Graph:
        """
        Convert a list of nodes and edges from Neo4j format to a NetworkX graph.

        Args:
            nodes_and_edges: List of dictionaries containing node_id, node_labels, rel_type, and target_id

        Returns:
            NetworkX graph representation
        """
        G = nx.Graph()
        nodes: Dict[int, Dict] = {}  # Store node data including degree

        # First pass: collect all nodes and their degrees
        for record in nodes_and_edges:
            node_id = record["node_id"]
            if node_id not in nodes:
                nodes[node_id] = {
                    "labels": set(record["node_labels"]),
                    **record["node_properties"],
                }

        # Add nodes to graph
        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)

        # Add edges
        for record in nodes_and_edges:
            if record["target_id"] is not None:
                G.add_edge(
                    record["node_id"], record["target_id"], type=record["rel_type"]
                )

        return G

    @staticmethod
    def _build_networkx_graph(result) -> nx.Graph:
        G = nx.Graph()
        nodes: Dict[int, Dict] = {}  # Store node data including degree

        # First pass: collect all nodes and their degrees
        records = list(result)  # Materialize results
        for record in records:
            node_id = record["node_id"]
            if node_id not in nodes:
                nodes[node_id] = {"labels": set(record["node_labels"])}

        # Add nodes to graph
        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)

        # Add edges
        for record in records:
            logging.debug(f"record: {record}")
            if record["target_id"] is not None:
                G.add_edge(
                    record["node_id"], record["target_id"], type=record["rel_type"]
                )

        return G
