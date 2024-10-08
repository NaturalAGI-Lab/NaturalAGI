import networkx as nx
from typing import Dict, Any


class GraphDeserializer:
    @staticmethod
    def deserialize(graph_dict: Dict[str, Any]) -> nx.Graph:
        """
        Deserialize a JSON string to a NetworkX graph.

        :param json_str: JSON string representation of the graph
        :return: Deserialized NetworkX graph
        """
        # Convert the dictionary back to a graph
        return nx.node_link_graph(graph_dict)
