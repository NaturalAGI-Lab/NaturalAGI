import networkx as nx
from typing import Dict, Any

class GraphSerializer:
    @staticmethod
    def serialize(graph: nx.Graph) -> Dict[str, Any]:
        """
        Serialize a NetworkX graph to a JSON string.
        
        :param graph: NetworkX graph to serialize
        :return: JSON string representation of the graph
        """
        # Convert node positions to strings (JSON keys must be strings)
        graph = nx.relabel_nodes(graph, {0: 'x', 1: 'y'})
        
        # Convert the graph to a dictionary
        graph_dict = nx.node_link_data(graph)
        
        # Serialize to JSON
        return graph_dict