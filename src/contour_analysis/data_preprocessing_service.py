from service.graph_persistance_service import GraphPersistenceService
import networkx as nx
from common.decorator import timed


class DataPreprocessingService:
    def __init__(self, graph_persistence_service: GraphPersistenceService):
        self.graph_persistence_service = graph_persistence_service

    @timed(label="DataPreprocessingService.persist_graph")
    def persist_graph(
        self,
        graph: nx.Graph,
        image_id: str,
        session_id: str,
        image_path: str | None = None,
    ) -> None:
        self.graph_persistence_service.save_graph_to_neo4j(
            graph, image_id, session_id, image_path
        )
