import logging
from neo4j import ManagedTransaction
from .base_analyzer import BaseAnalyzer
from common.model import ContourType


class ContourTypeAnalyzer(BaseAnalyzer):
    def analyze(self) -> ContourType:
        contour_type = self._analyze_contour_type()
        return contour_type

    def _analyze_contour_type(self) -> ContourType:
        logging.info("Analyzing contour type")
        if all(self.graph.degree(node) == 2 for node in self.graph.nodes()):
            return ContourType.CLOSED
        else:
            return ContourType.OPEN

    def persist(
        self,
        mx: ManagedTransaction,
        session_id: str,
        image_id: str,
        result: ContourType,
    ):
        query = """
            CALL {
                MATCH (n:Point {image_id: $image_id})
                SET n.contour_type = $result
            }
            CALL {
                MATCH (n:Vector {image_id: $image_id})
                SET n.contour_type = $result
            }
        """
        mx.run(query, image_id=image_id, result=result.value)
