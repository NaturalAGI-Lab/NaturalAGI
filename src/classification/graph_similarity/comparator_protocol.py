from typing import Protocol

import networkx as nx


class GraphComparator(Protocol):
    def compare(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
    ) -> float: ...
