from typing import Dict, Any, List

from neo4j import ManagedTransaction
from visitors.visitor import Visitor
from model.vector import Vector
from model.feature.length_comparison_result import LengthComparisonResult


class LengthComparisonVisitor(Visitor):
    def __init__(self) -> None:
        self.previous_length: float = 0.0
        self.length_comparisons: Dict[str, str] = {}
        self.line_ids: List[str] = []

    def visit_point(self, point: Any) -> Any:
        # This visitor does not handle points
        return None

    def visit_line(self, line: Vector) -> Dict[str, Any]:
        comparison = LengthComparisonResult.N_A
        if self.previous_length:
            if line.length > self.previous_length:
                comparison = LengthComparisonResult.LONGER
            elif line.length < self.previous_length:
                comparison = LengthComparisonResult.SHORTER
            else:
                comparison = LengthComparisonResult.EQUAL
        self.length_comparisons[line.id] = comparison
        self.previous_length = line.length
        self.line_ids.append(line.id)

        return {
            "length_comparison": comparison,
            "line1_id": self.line_ids[-2],
            "line2_id": self.line_ids[-1],
        }

    def save_result(self, tx: ManagedTransaction, image_id: str, session_id: str, result: Dict[str, Any]) -> None:
        query = """
        MATCH (v1:Vector {id: $line1_id}), (v2:Vector {id: $line2_id})
        MERGE (v1)-[:COMPARES_TO]->(v2)
        ON CREATE SET v1.length_comparison = $comparison, v1.session_id = $session_id, v1.image_id = $image_id
        """
        tx.run(
            query,
            line1_id=result["line1_id"],
            line2_id=result["line2_id"],
            comparison=result["length_comparison"].value,
            image_id=image_id,
            session_id=session_id,
        )

    def get_results(self) -> Dict[str, str]:
        return self.length_comparisons

    def reset(self) -> None:
        self.previous_length = 0.0
        self.length_comparisons.clear()
