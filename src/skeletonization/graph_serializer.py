import json
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
        graph = nx.relabel_nodes(graph, lambda x: str(tuple(x)))
        
        # Convert the graph to a dictionary
        graph_dict = nx.node_link_data(graph)
        
        # Serialize to JSON
        return graph_dict

    @staticmethod
    def deserialize(graph_dict: Dict[str, Any]) -> nx.Graph:
        """
        Deserialize a JSON string to a NetworkX graph.
        
        :param json_str: JSON string representation of the graph
        :return: Deserialized NetworkX graph
        """
        # Convert the dictionary back to a graph
        graph = nx.node_link_graph(graph_dict)
        
        # Convert node labels back to tuples of floats
        graph = nx.relabel_nodes(graph, lambda x: tuple(map(float, x.strip('()').split(','))))
        
        return graph