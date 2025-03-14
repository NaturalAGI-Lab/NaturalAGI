from ast import Dict
import hashlib
import json
import networkx as nx

class UUIDGenerator:
    
    @staticmethod
    def generate_concept_id(graph: nx.Graph) -> str:
        """
        Generate a deterministic ID for the concept based on its graph structure.
        """
        # Create a dictionary representation of the graph
        graph_dict = {"nodes": [], "edges": []}

        # Sort nodes by their degree and properties for deterministic ordering
        sorted_nodes = sorted(
            graph.nodes(data=True),
            key=lambda n: (graph.degree(n[0]), UUIDGenerator._sort_dict(n[1])),
        )

        for i, (node, attrs) in enumerate(sorted_nodes):
            node_dict = {"id": i}
            node_dict.update(attrs)
            graph_dict["nodes"].append(node_dict)

        # Create a mapping from original node IDs to sorted IDs
        node_mapping = {node: i for i, (node, _) in enumerate(sorted_nodes)}

        # Sort edges for deterministic ordering
        sorted_edges = []
        for u, v, attrs in graph.edges(data=True):
            sorted_edges.append(
                (
                    min(node_mapping[u], node_mapping[v]),
                    max(node_mapping[u], node_mapping[v]),
                    attrs,
                )
            )

        sorted_edges.sort(key=lambda e: (e[0], e[1], UUIDGenerator._sort_dict(e[2])))

        for u, v, attrs in sorted_edges:
            edge_dict = {"source": u, "target": v}
            edge_dict.update(attrs)
            graph_dict["edges"].append(edge_dict)

        # Create a deterministic JSON string and hash it
        graph_json = json.dumps(graph_dict, sort_keys=True)
        concept_id = hashlib.sha256(graph_json.encode()).hexdigest()

        return concept_id
    
    @staticmethod
    def _sort_dict(self, d: Dict) -> str:
        """Helper method to convert a dictionary to a deterministic string representation."""
        return json.dumps(d, sort_keys=True)