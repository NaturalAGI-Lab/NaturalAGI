from typing import Dict, Any, List

from neo4j import ManagedTransaction
from .visitor import Visitor
from ...model.point import Point
from ...model.vector import Vector
from ...model.length_comparison_result import LengthComparisonResult


class LengthComparisonVisitor(Visitor):
    def __init__(self) -> None:
        self.previous_length: float = 0.0
        self.length_comparisons: Dict[str, str] = {}
        self.line_ids: List[str] = []

    def visit_point(self, point: Any) -> Any:
        # This visitor does not handle points
        return None

    def visit_line(self, line: Vector, start_point: Point) -> Dict[str, Any]:
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

        if len(self.line_ids) < 2:
            return None

        return {
            "length_comparison": comparison,
            "line1_id": self.line_ids[-2],
            "line2_id": self.line_ids[-1],
        }

    def save_result(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        query = """
            MATCH (v1:Vector {id: $line1_id})--(:Point)--(v2:Vector {id: $line2_id})
            MERGE (vc:VectorComparison:Feature {
                from_vector: $line1_id,
                to_vector: $line2_id,
                session_id: $session_id
            })
            ON CREATE SET vc.value = $comparison,
                        vc.image_id = $image_id,
                        vc.samples = [$image_id],
                        v1.length = $length1,
                        v2.length = $length2
            ON MATCH SET vc.samples = CASE
                WHEN NOT $image_id IN vc.samples THEN vc.samples + $image_id
                ELSE vc.samples
            END,
            v1.length = $length1,
            v2.length = $length2
            MERGE (v1)-[:HAS_COMPARISON]->(vc)-[:COMPARES_TO]->(v2)
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
