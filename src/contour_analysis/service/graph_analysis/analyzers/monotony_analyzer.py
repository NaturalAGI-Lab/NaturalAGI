import logging
from typing import Tuple

from neo4j import ManagedTransaction
from .base_analyzer import BaseAnalyzer
from common.model import ContourDevelopment


class MonotonyAnalyzer(BaseAnalyzer):
    def analyze(self) -> ContourDevelopment:
        contour_development = self._analyze_contour_development()
        return contour_development

    def _analyze_contour_development(self) -> ContourDevelopment:
        logging.info("Analyzing contour development")
        vector_directions = set()
        for edge in self.graph.edges():
            direction = self._calculate_direction(*edge)
            vector_directions.add(direction)

        if len(vector_directions) == 0:
            logging.warning("No vector directions found")
            return ContourDevelopment.UNKNOWN
        elif len(vector_directions) == 1:
            return ContourDevelopment.MONOTONIC
        else:
            return ContourDevelopment.NON_MONOTONIC

    def _calculate_direction(self, u, v):
        u_data = self.graph.nodes[u]
        v_data = self.graph.nodes[v]
        dx = v_data['x'] - u_data['x']
        dy = v_data['y'] - u_data['y']
        return (dx, dy)

    def persist(
        self,
        mx: ManagedTransaction,
        session_id: str,
        image_id: str,
        result: ContourDevelopment,
    ):
        query = """
            CALL {
                MATCH (n:Point {image_id: $image_id})
                SET n.monotony = $result
            }
            CALL {
                MATCH (n:Vector {image_id: $image_id})
                SET n.monotony = $result
            }
        """
        mx.run(query, image_id=image_id, result=result.value)
