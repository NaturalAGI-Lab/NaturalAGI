import networkx as nx

from services.graph_complexity_service import GraphComplexityService

class ComplexityPreprocessor:
    def __init__(self, graph_complexity_service: GraphComplexityService):
        self.graph_complexity_service = graph_complexity_service

    def is_concept_more_complex(self, concept_graph: nx.Graph, image_graph: nx.Graph) -> bool:
        concept_complexity = self.graph_complexity_service.get_default_graph_complexity(concept_graph)
        image_complexity = self.graph_complexity_service.get_default_graph_complexity(image_graph)
        return concept_complexity > image_complexity
