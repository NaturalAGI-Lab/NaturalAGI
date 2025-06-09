import logging
import networkx as nx
import numpy as np
from common.critical_point import CriticalPointType
from services.start_point_service import StartPointService


class StartPointPreprocessor:

    @staticmethod
    def preprocess(inference_graph: nx.Graph, concept_graph: nx.Graph) -> nx.Graph:
        logger = logging.getLogger(__name__)
        logger.info("Preprocessing start point")

        concept_start_point = StartPointPreprocessor._find_start_point(concept_graph)
        if concept_start_point is None:
            raise ValueError("Concept start point not found")

        centroid = concept_graph.nodes[concept_start_point]["centroid"]
        centroid = np.array(centroid)
        logger.info(f"Centroid: {centroid}")
        start_point_service = StartPointService(centroid=centroid)

        start_point = start_point_service.get_start_point(inference_graph)
        logger.info(f"New start point: {start_point}")
        inference_graph = start_point_service.change_start_point(
            inference_graph, start_point
        )
        return inference_graph

    @staticmethod
    def _find_start_point(graph: nx.Graph) -> int:
        for node, data in graph.nodes(data=True):
            if CriticalPointType.START_POINT.value in data["labels"]:
                return node
        return None
