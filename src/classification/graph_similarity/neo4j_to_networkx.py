import json
import logging
from typing import Dict
import networkx as nx
from neo4j import Result

logging.basicConfig(level=logging.INFO)


class Neo4jToNetworkX:
    """Responsible for converting Neo4j graphs to NetworkX format"""

    @staticmethod
    def build_networkx_graph(result: Result, is_concept: bool = False) -> nx.Graph:
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
                "is_concept": is_concept,
                **parsed_properties,
            }
            nodes[node_id] = node_data

        for node_id, node_data in nodes.items():
            G.add_node(node_id, **node_data)

        for record in records:
            # Add regular edges
            if record["target_id"] is not None and record["rel_id"] is not None:
                G.add_edge(
                    record["node_id"],
                    record["target_id"],
                    type=record["rel_type"],
                    id=record["rel_id"],
                    source=record["node_id"],
                    target=record["target_id"],
                    is_concept=is_concept,
                )
        return G
