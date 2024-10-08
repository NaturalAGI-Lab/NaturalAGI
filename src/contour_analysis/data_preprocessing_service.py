from service.graph_persistance_service import GraphPersistenceService
import networkx as nx

class DataPreprocessingService:
    def __init__(self, graph_persistence_service: GraphPersistenceService):
        self.graph_persistence_service = graph_persistence_service

    def persist_graph(self, graph: nx.Graph, image_id: str, session_id: str) -> None:
        self.graph_persistence_service.save_graph_to_neo4j(graph, image_id, session_id)

