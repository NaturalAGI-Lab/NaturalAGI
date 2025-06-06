import networkx as nx
import json
import numpy as np
from enum import Enum


class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class GraphSaver:
    @staticmethod
    def save_graph_json(graph: nx.Graph, filename: str):
        data = nx.node_link_data(graph)
        with open(filename, "w") as f:
            json.dump(data, f, indent=2, cls=NumpyJSONEncoder)
