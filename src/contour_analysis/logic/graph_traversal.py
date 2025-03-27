from typing import Generator, Any, Tuple, Optional
import networkx as nx

from model.point import Point
from model.vector import Vector, HorizontalDirection, VerticalDirection


class GraphTraversal:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def calculate_direction(
        self, x1: float, y1: float, x2: float, y2: float
    ) -> Tuple[HorizontalDirection, VerticalDirection]:
        """
        Calculate the horizontal and vertical direction of movement from point (x1, y1) to (x2, y2).

        Args:
            x1 (float): X-coordinate of the start point
            y1 (float): Y-coordinate of the start point
            x2 (float): X-coordinate of the end point
            y2 (float): Y-coordinate of the end point

        Returns:
            Tuple[HorizontalDirection, VerticalDirection]: The horizontal and vertical directions
        """
        # Calculate horizontal direction
        if x2 > x1:
            h_direction = HorizontalDirection.RIGHT
        elif x2 < x1:
            h_direction = HorizontalDirection.LEFT
        else:
            h_direction = HorizontalDirection.NONE

        # Calculate vertical direction
        if y2 > y1:
            v_direction = (
                VerticalDirection.BOTTOM
            )  # In image coordinates, y increases downward
        elif y2 < y1:
            v_direction = VerticalDirection.TOP
        else:
            v_direction = VerticalDirection.NONE

        return h_direction, v_direction

    def dfs_traversal(
        self, start_node: Any
    ) -> Generator[Tuple[Point, Optional[Vector]], None, None]:
        visited_edges = set()

        def find_edge(x1: float, y1: float, x2: float, y2: float) -> Optional[dict]:
            for _, _, edge_data in self.graph.edges(data=True):
                if (
                    edge_data["x1"] == x1
                    and edge_data["y1"] == y1
                    and edge_data["x2"] == x2
                    and edge_data["y2"] == y2
                ) or (
                    edge_data["x1"] == x2
                    and edge_data["y1"] == y2
                    and edge_data["x2"] == x1
                    and edge_data["y2"] == y1
                ):
                    return edge_data
            return None

        def _dfs(
            node_id: str, prev_x: Optional[float] = None, prev_y: Optional[float] = None
        ):
            node_data = self.graph.nodes[node_id]
            point = Point(
                id=node_data["uuid"],
                x=node_data["x"],
                y=node_data["y"],
                nx_id=node_id,
            )

            incoming_vector = None
            if prev_x is not None and prev_y is not None:
                edge_data = find_edge(prev_x, prev_y, point.x, point.y)
                if edge_data:
                    # Calculate direction of the vector
                    h_direction, v_direction = self.calculate_direction(
                        prev_x, prev_y, point.x, point.y
                    )

                    incoming_vector = Vector(
                        id=edge_data["uuid"],
                        x1=prev_x,
                        y1=prev_y,
                        x2=point.x,
                        y2=point.y,
                        length=edge_data["length"],
                        horizontal_direction=h_direction,
                        vertical_direction=v_direction,
                    )
                else:
                    raise ValueError(
                        f"Edge not found between {prev_x}, {prev_y} and {point.x}, {point.y}"
                    )

            yield point, incoming_vector

            for neighbor_id in self.graph.neighbors(node_id):
                edge = tuple(sorted([node_id, neighbor_id]))
                if edge not in visited_edges:
                    visited_edges.add(edge)
                    yield from _dfs(neighbor_id, point.x, point.y)

        yield from _dfs(start_node)
