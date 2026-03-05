import networkx as nx

from .graph_edit_distance_comparator import GraphEditDistanceComparator


class GEDComparator:

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def compare(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
    ) -> float:
        return GraphEditDistanceComparator.compare_graphs_ged(
            image_graph=image_graph,
            concept_graph=concept_graph,
            concept_name=concept_name,
            ged_timeout=self.timeout,
        )
