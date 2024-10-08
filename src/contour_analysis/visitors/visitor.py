from abc import ABC, abstractmethod
from typing import Any, Dict
from model.point import Point
from model.vector import Vector

class Visitor(ABC):
    @abstractmethod
    def visit_point(self, point: Point) -> None:
        pass

    @abstractmethod
    def visit_line(self, line: Vector) -> None:
        pass
    
    def get_results(self) -> Dict[str, Any]:
        pass
    
    def reset(self) -> None:
        """Reset the internal state of the visitor."""
        pass