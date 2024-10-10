import logging
from typing import Tuple

from neo4j import ManagedTransaction
from .base_analyzer import BaseAnalyzer
from common.models import ContourDevelopment


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
            MERGE (contour_development:ContourDevelopment:Feature {
                session_id: $session_id,
                value: $result
            })
            ON CREATE SET contour_development.samples = [$image_id]
            ON MATCH SET contour_development.samples = CASE
                WHEN NOT $image_id IN contour_development.samples THEN contour_development.samples + $image_id
                ELSE contour_development.samples
            END
        """
        mx.run(query, session_id=session_id, result=result.name, image_id=image_id)
