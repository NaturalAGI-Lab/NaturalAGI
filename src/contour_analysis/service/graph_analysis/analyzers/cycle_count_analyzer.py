import logging
from typing import List
from neo4j import ManagedTransaction
import networkx as nx

from .base_analyzer import BaseAnalyzer

logging.basicConfig(level=logging.INFO)

class CycleCountAnalyzer(BaseAnalyzer):
    def analyze(self) -> int:
        cycle_count = self._count_cycles()
        return cycle_count

    def _count_cycles(self) -> int:
        logging.info("Analyzing cycles in contour")
        try:
            # Find all elementary cycles in the graph
            cycles = list(nx.simple_cycles(self.graph))
            cycle_count = len(cycles)
            logging.info(f"Found {cycle_count} cycles in the contour")
            return cycle_count
        except nx.NetworkXError:
            logging.warning("Unable to analyze cycles, graph might be invalid")
            return 0

    def persist(
        self,
        mx: ManagedTransaction,
        session_id: str,
        image_id: str,
        result: int
    ) -> None:
        query = """
            MERGE (cycle_count_feature:CycleCount:Feature {
                session_id: $session_id,
                value: $result
            })
            ON CREATE SET cycle_count_feature.samples = [$image_id]
            ON MATCH SET cycle_count_feature.samples = CASE
                WHEN NOT $image_id IN cycle_count_feature.samples THEN cycle_count_feature.samples + $image_id
                ELSE cycle_count_feature.samples
            END
        """
        mx.run(
            query,
            session_id=session_id,
            result=result,
            image_id=image_id
        )
        query = """
            MATCH (n {session_id: $session_id})
            WHERE n:Point or n:Vector
            SET n.cycle_count = $result
        """
        mx.run(query, session_id=session_id, result=result)
