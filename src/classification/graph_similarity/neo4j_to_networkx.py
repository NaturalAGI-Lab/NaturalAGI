import json
import logging
from typing import Dict
import networkx as nx
from neo4j import Session, Result

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
        WITH n, labels(n) as node_labels, properties(n) as node_props
        OPTIONAL MATCH (n)-[r]-(m {image_id: $image_id})
        WITH n, node_labels, r, m, node_props
        RETURN elementId(n) AS node_id, 
               node_labels,
               node_props,
               type(r) AS rel_type, 
               elementId(m) AS target_id
        """
        result = session.run(query, image_id=image_id)
        return Neo4jToNetworkX.build_networkx_graph(result)

    @staticmethod
    def build_networkx_graph(result: Result) -> nx.Graph:
        """
        Builds a NetworkX graph from a Neo4j result that includes segments.
        This is used by extract_concept_graph.
        """
        G = nx.Graph()
        nodes: Dict[int, Dict] = {}
        records = list(result)  # Materialize results

        for record in records:
            node_id = record["node_id"]
            properties = record["node_props"]
            # Parse properties: try to parse string values as JSON
            parsed_properties = {}
            for key, value in properties.items():
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                        parsed_properties[key] = parsed_value
                    except json.JSONDecodeError:
                        parsed_properties[key] = value
                else:
                    parsed_properties[key] = value
            # Set 'labels' property
            parsed_properties["labels"] = record["node_labels"]
            node_data = {
                "labels": set(record["node_labels"]),
                **parsed_properties,
            }
            nodes[node_id] = node_data

        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)

        for record in records:
            # Add regular edges
            if record["target_id"] is not None:
                G.add_edge(
                    record["node_id"], record["target_id"], type=record["rel_type"]
                )
        return G
