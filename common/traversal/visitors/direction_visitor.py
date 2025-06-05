from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
from neo4j import ManagedTransaction
from .visitor import Visitor
from ...model.point import Point
from ...model.vector import Vector, HorizontalDirection, VerticalDirection


class DirectionVisitor(Visitor):
    def __init__(self, graph: nx.Graph):
        super().__init__(graph)
        self.directions: Dict[str, Dict[str, str]] = {}
        self.directions_sequence: List[Dict[str, Any]] = []
        self.current_sequence_index = 0

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

    def visit_point(self, _: Point) -> None:
        # No specific operation for points in this visitor
        return None

    def visit_line(self, line: Vector) -> Dict[str, Any]:
        # Extract direction information
        h_direction, v_direction = self.calculate_direction(
            line.x1, line.y1, line.x2, line.y2
        )
        line.horizontal_direction = h_direction
        line.vertical_direction = v_direction

        # Store the direction for this vector
        self.directions[line.id] = {"horizontal": h_direction, "vertical": v_direction}
        self.graph.nodes[line.id]["horizontal_direction"] = h_direction
        self.graph.nodes[line.id]["vertical_direction"] = v_direction
        self.graph.nodes[line.id][
            "direction_sequence_index"
        ] = self.current_sequence_index
        # Add to the sequence
        sequence_info = {
            "index": self.current_sequence_index,
            "line_id": line.id,
            "horizontal_direction": h_direction,
            "vertical_direction": v_direction,
            "x1": line.x1,
            "y1": line.y1,
            "x2": line.x2,
            "y2": line.y2,
        }

        self.directions_sequence.append(sequence_info)
        self.current_sequence_index += 1

        return {
            "line_id": line.id,
            "horizontal_direction": h_direction,
            "vertical_direction": v_direction,
            "sequence_index": self.current_sequence_index - 1,
        }

    def save_result(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Optional[Dict[str, Any]],
    ) -> None:
        if not result:
            return

        # Set direction properties on the Vector node
        set_direction_query = """
        MATCH (v:Vector {id: $id})
        SET v.horizontal_direction = $horizontal_direction,
            v.vertical_direction = $vertical_direction,
            v.direction_sequence_index = $sequence_index
        """

        tx.run(
            set_direction_query,
            id=result["line_id"],
            horizontal_direction=result["horizontal_direction"],
            vertical_direction=result["vertical_direction"],
            sequence_index=result["sequence_index"],
        )

        # # Create DirectionFeature nodes and relationships
        # create_h_direction_feature = """
        # MATCH (v:Vector {id: $id})
        # MERGE (f:HorizontalDirection:Feature {value: $direction, session_id: $session_id})
        # ON CREATE SET f.samples = [$image_id]
        # ON MATCH SET f.samples = CASE
        #     WHEN NOT $image_id IN f.samples THEN f.samples + $image_id
        #     ELSE f.samples
        # END
        # MERGE (v)-[:HAS_HORIZONTAL_DIRECTION]->(f)
        # """

        # create_v_direction_feature = """
        # MATCH (v:Vector {id: $id})
        # MERGE (f:VerticalDirection:Feature {value: $direction, session_id: $session_id})
        # ON CREATE SET f.samples = CASE
        #     WHEN NOT $image_id IN f.samples THEN f.samples + $image_id
        #     ELSE f.samples
        # END
        # MERGE (v)-[:HAS_VERTICAL_DIRECTION]->(f)
        # """

        # tx.run(
        #     create_h_direction_feature,
        #     id=result["line_id"],
        #     direction=result["horizontal_direction"],
        #     session_id=session_id,
        #     image_id=image_id,
        # )

        # tx.run(
        #     create_v_direction_feature,
        #     id=result["line_id"],
        #     direction=result["vertical_direction"],
        #     session_id=session_id,
        #     image_id=image_id,
        # )

    def get_results(self) -> Dict[str, Any]:
        return {"directions": self.directions, "sequence": self.directions_sequence}

    def reset(self) -> None:
        self.directions = {}
        self.directions_sequence = []
        self.current_sequence_index = 0
