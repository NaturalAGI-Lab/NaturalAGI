import networkx as nx
import json


class GraphSaver:
    @staticmethod
    def save_graph_json(graph: nx.Graph, filename: str):
        data = nx.node_link_data(graph)
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
