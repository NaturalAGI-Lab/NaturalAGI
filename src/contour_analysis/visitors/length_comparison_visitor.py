from typing import Dict, Any
from visitors.visitor import Visitor
from model.vector import Vector
from model.feature.length_comparison_result import LengthComparisonResult
class LengthComparisonVisitor(Visitor):
    def __init__(self) -> None:
        self.previous_length: float = 0.0
        self.length_comparisons: Dict[str, str] = {}

    def visit_point(self, point: Any) -> None:
        # This visitor does not handle points
        pass

    def visit_line(self, line: Vector) -> None:
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

    def get_results(self) -> Dict[str, str]:
        return self.length_comparisons

    def reset(self) -> None:
        self.previous_length = 0.0
        self.length_comparisons.clear()