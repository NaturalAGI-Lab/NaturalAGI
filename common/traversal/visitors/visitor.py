from abc import ABC, abstractmethod
from typing import Any, Dict

import networkx as nx
from neo4j import ManagedTransaction
from ...model.point import Point
from ...model.vector import Vector


class Visitor(ABC):
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    @abstractmethod
    def visit_point(self, point: Point) -> Any:
        pass

    @abstractmethod
    def visit_line(self, line: Vector) -> Any:
        pass

    @abstractmethod
    def save_result(
        self, tx: ManagedTransaction, image_id: str, session_id: str, result: Any
    ) -> None:
        pass

    def get_results(self) -> Dict[str, Any]:
        pass

    def reset(self) -> None:
        """Reset the internal state of the visitor."""
        pass
