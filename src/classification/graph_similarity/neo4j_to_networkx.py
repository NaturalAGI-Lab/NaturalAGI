import logging
from typing import Dict
import networkx as nx
from neo4j import Session

logging.basicConfig(level=logging.INFO)

class Neo4jToNetworkX:
    """Responsible for converting Neo4j graphs to NetworkX format"""

    @staticmethod
    def extract_image_graph(session: Session, image_id: str) -> nx.Graph:
        """
        Extracts a graph from Neo4j for a given image_id and converts it to NetworkX format.
        This version excludes segment embedding (i.e. no Segment nodes or HAS_RELATIVE_POSITION edges).
        """
        query = """
        MATCH (n {image_id: $image_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) AS node_labels
        OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
        WITH n, node_labels, r, m
        RETURN id(n) AS node_id, 
               node_labels,
               type(r) AS rel_type, 
               id(m) AS target_id
        """
        result = session.run(query, image_id=image_id)
        return Neo4jToNetworkX._build_networkx_graph_without_segments(result)

    @staticmethod
    def extract_concept_graph(session: Session, concept_id: str) -> nx.Graph:
        """Extract graph from Neo4j (with segments) for a given concept_id and convert to NetworkX format."""
        query = """
        MATCH (n {concept_id: $concept_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) AS node_labels
        OPTIONAL MATCH (n)-[r]-(m {concept_id: $concept_id})
        WITH n, node_labels, r, m
        OPTIONAL MATCH (n)-[:HAS_RELATIVE_POSITION]->(s:Segment)
        WITH n, node_labels, r, m, s, 
             CASE WHEN s IS NOT NULL THEN labels(s) ELSE [] END AS segment_labels
        RETURN id(n) AS node_id, 
               node_labels,
               type(r) AS rel_type, 
               id(m) AS target_id,
               id(s) AS segment_id,
               segment_labels
        """
        result = session.run(query, concept_id=concept_id)
        return Neo4jToNetworkX._build_networkx_graph(result)

    @staticmethod
    def _build_networkx_graph_without_segments(result) -> nx.Graph:
        """
        Builds a NetworkX graph from a Neo4j result that does not include segment embeddings.
        Only nodes of type Point or Vector and their interconnections are added.
        """
        G = nx.Graph()
        nodes: Dict[int, Dict] = {}
        
        records = list(result)
        # First pass: collect nodes
        for record in records:
            node_id = record["node_id"]
            if node_id not in nodes:
                nodes[node_id] = {"labels": set(record["node_labels"])}
        
        # Add nodes to graph
        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)
        
        # Add edges (only regular edges, no segment edges)
        for record in records:
            if record["target_id"] is not None:
                G.add_edge(
                    record["node_id"],
                    record["target_id"],
                    type=record["rel_type"]
                )
        return G

    @staticmethod
    def _build_networkx_graph(result) -> nx.Graph:
        """
        Builds a NetworkX graph from a Neo4j result that includes segments.
        This is used by extract_concept_graph.
        """
        G = nx.Graph()
        nodes: Dict[int, Dict] = {}
        records = list(result)  # Materialize results

        for record in records:
            node_id = record["node_id"]
            if node_id not in nodes:
                nodes[node_id] = {"labels": set(record["node_labels"])}
            # Add segment nodes if they exist
            segment_id = record["segment_id"]
            if segment_id is not None and segment_id not in nodes:
                segment_labels = set(record["segment_labels"])
                segment_labels.add("Segment")  # Ensure the Segment label is present
                nodes[segment_id] = {"labels": segment_labels}

        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)

        for record in records:
            # Add regular edges
            if record["target_id"] is not None:
                G.add_edge(
                    record["node_id"],
                    record["target_id"],
                    type=record["rel_type"]
                )
            # Add segment edges
            if record["segment_id"] is not None:
                G.add_edge(
                    record["node_id"],
                    record["segment_id"],
                    type="HAS_RELATIVE_POSITION"
                )
        return G