import logging
from typing import Dict
import networkx as nx
from neo4j import Session

logging.basicConfig(level=logging.INFO)


class Neo4jToNetworkX:
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
        OPTIONAL MATCH (n)-[:HAS_RELATIVE_POSITION]->(s:Segment)
        WITH n, node_labels, r, m, s, 
             CASE WHEN s IS NOT NULL THEN labels(s) ELSE [] END as segment_labels
        RETURN id(n) as node_id, 
               node_labels,
               type(r) as rel_type, 
               id(m) as target_id,
               id(s) as segment_id,
               segment_labels
        """
        result = session.run(query, image_id=image_id)
        return Neo4jToNetworkX._build_networkx_graph(result)

    @staticmethod
    def extract_concept_graph(session: Session, concept_id: str) -> nx.Graph:
        """Extract graph from Neo4j and convert to NetworkX format."""
        query = """
        MATCH (n {concept_id: $concept_id})
        WHERE n:Point OR n:Vector
        WITH n, labels(n) as node_labels
        OPTIONAL MATCH (n)-[r]-(m {concept_id: $concept_id})
        WITH n, node_labels, r, m
        OPTIONAL MATCH (n)-[:HAS_RELATIVE_POSITION]->(s:Segment)
        WITH n, node_labels, r, m, s, 
             CASE WHEN s IS NOT NULL THEN labels(s) ELSE [] END as segment_labels
        RETURN id(n) as node_id, 
               node_labels,
               type(r) as rel_type, 
               id(m) as target_id,
               id(s) as segment_id,
               segment_labels
        """
        result = session.run(query, concept_id=concept_id)
        return Neo4jToNetworkX._build_networkx_graph(result)

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

            # Add segment nodes if they exist
            segment_id = record["segment_id"]
            if segment_id is not None and segment_id not in nodes:
                segment_labels = set(record["segment_labels"])
                segment_labels.add("Segment")  # Ensure Segment label is present
                nodes[segment_id] = {"labels": segment_labels}

        # Add nodes to graph
        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)

        # Add edges
        for record in records:
            # Add regular edges
            if record["target_id"] is not None:
                G.add_edge(
                    record["node_id"], record["target_id"], type=record["rel_type"]
                )

            # Add segment edges
            if record["segment_id"] is not None:
                G.add_edge(
                    record["node_id"],
                    record["segment_id"],
                    type="HAS_RELATIVE_POSITION",
                )

        return G
