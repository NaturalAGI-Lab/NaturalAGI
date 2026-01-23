import networkx as nx
from typing import Dict, Any
import numpy as np

class GraphSerializer:
    @staticmethod
    def _convert_numpy_types(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: GraphSerializer._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [GraphSerializer._convert_numpy_types(item) for item in obj]
        return obj

    @staticmethod
    def serialize(graph: nx.Graph) -> Dict[str, Any]:
        graph = nx.relabel_nodes(graph, {0: 'x', 1: 'y'})
        graph_dict = nx.node_link_data(graph)
        return GraphSerializer._convert_numpy_types(graph_dict)