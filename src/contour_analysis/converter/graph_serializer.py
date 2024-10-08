import json
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
        graph = nx.node_link_graph(graph_dict)

        # Convert node labels back to tuples of floats
        graph = nx.relabel_nodes(graph, lambda x: tuple(x))

        return graph
