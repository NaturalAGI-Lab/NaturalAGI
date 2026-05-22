import logging
from typing import Optional
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
        raw_degree = concept_graph.nodes[concept_start_point].get("expected_start_degree")
        expected_start_degree = StartPointPreprocessor._parse_expected_degree(raw_degree)
        logger.info(f"Centroid: {centroid}, Expected start degree: {expected_start_degree}")
        start_point_service = StartPointService(
            centroid=centroid,
            expected_start_degree=expected_start_degree,
        )

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

    @staticmethod
    def _parse_expected_degree(raw_value) -> Optional[int]:
        if raw_value is None:
            return None
        if isinstance(raw_value, (int, float)):
            return int(raw_value)
        if isinstance(raw_value, dict) and "center" in raw_value:
            return int(raw_value["center"])
        return None
