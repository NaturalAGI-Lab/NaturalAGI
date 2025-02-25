import logging
from neo4j import ManagedTransaction
import networkx as nx
from .base_analyzer import BaseAnalyzer
from common.models import ContourType

class ContourTypeAnalyzer(BaseAnalyzer):
    def analyze(self) -> ContourType:
        contour_type = self._analyze_contour_type()
        return contour_type

    def _analyze_contour_type(self) -> ContourType:
        logging.info("Analyzing contour type")
        if nx.is_connected(self.graph) and all(
            self.graph.degree(node) == 2 for node in self.graph.nodes()
        ):
            return ContourType.CLOSED
        else:
            return ContourType.OPEN
        
    def persist(self, mx: ManagedTransaction, session_id: str, image_id: str, result: ContourType):
        query = """
            MERGE (contour_type:ContourType:Feature {
                session_id: $session_id,
                value: $result
            })
            ON CREATE SET contour_type.samples = [$image_id]
            ON MATCH SET contour_type.samples = CASE
                WHEN NOT $image_id IN contour_type.samples THEN contour_type.samples + $image_id
                ELSE contour_type.samples
            END
        """
        mx.run(query, session_id=session_id, result=result.name, image_id=image_id)
        query = """
            MATCH (n {session_id: $session_id})
            WHERE n:Point or n:Vector
            SET n.contour_type = $result
        """
        mx.run(query, session_id=session_id, result=result.name)
