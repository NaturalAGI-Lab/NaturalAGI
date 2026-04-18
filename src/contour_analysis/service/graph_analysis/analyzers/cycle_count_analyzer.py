import logging
from neo4j import ManagedTransaction
import networkx as nx

from common.feature_scales import h_k

from .base_analyzer import BaseAnalyzer

logging.basicConfig(level=logging.INFO)


class CycleCountAnalyzer(BaseAnalyzer):
    def analyze(self) -> int:
        return self._count_cycles()

    def _count_cycles(self) -> int:
        logging.info("Analyzing cycles in contour")
        try:
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
        result: int,
    ) -> None:
        # h_k: saturating map v/(v+1) — raw count → u_k ∈ [0, 1).
        transformed = h_k("cycle_count", result)
        query = """
            CALL {
                MATCH (n:Point {image_id: $image_id})
                SET n.cycle_count = $val
            }
            CALL {
                MATCH (n:Vector {image_id: $image_id})
                SET n.cycle_count = $val
            }
        """
        mx.run(query, image_id=image_id, val=transformed)
