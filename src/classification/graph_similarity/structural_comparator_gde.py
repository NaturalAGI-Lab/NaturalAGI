import enum
import logging
from typing import Dict, Any, Set, List, Optional, FrozenSet
import networkx as nx
from neo4j import Session

from .neo4j_to_networkx import Neo4jToNetworkX

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ChangesCost(enum.Enum):
    NO_COST = 0.0
    MINOR = 0.1
    GENERAL = 1.0
    SEVERE = 3.0
    CRITICAL = 10.0
    IMPOSSIBLE = float("inf")

class StructuralComparator:
    @staticmethod
    def compare_graphs_ged(
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
        ged_timeout: float,
    ) -> float:
        logging.info(
            f"Comparing graph with concept {concept_name} using Graph Edit Distance"
        )

        score = StructuralComparator._compare_at_level(
            image_graph, concept_graph, ged_timeout=ged_timeout
        )

        logging.info(f"Original score: {score}")
        return score

    @staticmethod
    def _compare_at_level(
        image_graph: nx.Graph, concept_graph: nx.Graph, ged_timeout: float
    ) -> float:
        """Compare graphs at a specific abstraction level using Graph Edit Distance"""

        def node_subst_cost(node1_data: Dict, node2_data: Dict) -> float:
            """Calculate substitution cost between two nodes based on their labels and regions"""
            labels1 = node1_data.get("labels", set())
            labels2 = node2_data.get("labels", set())
            
            if labels1 == labels2:
                return ChangesCost.NO_COST.value

            # Only allow point-to-point, vector-to-vector and segment-to-segment comparisons
            is_vector1 = any("Vector" in label for label in labels1)
            is_vector2 = any("Vector" in label for label in labels2)
            is_point1 = any("Point" in label for label in labels1)
            is_point2 = any("Point" in label for label in labels2)
            is_segment1 = any("Segment" in label for label in labels1)
            is_segment2 = any("Segment" in label for label in labels2)
            
            if (is_vector1 and not is_vector2) or (not is_vector1 and is_vector2):
                return ChangesCost.IMPOSSIBLE.value
            if (is_point1 and not is_point2) or (not is_point1 and is_point2):
                return ChangesCost.IMPOSSIBLE.value
            if (is_segment1 and not is_segment2) or (not is_segment1 and is_segment2):
                return ChangesCost.IMPOSSIBLE.value
            
            # Handle Segment nodes - require exact match
            if "Segment" in labels1 or "Segment" in labels2:
                if labels1 != labels2:
                    return ChangesCost.SEVERE.value
                return ChangesCost.NO_COST.value

            is_simple_point1 = labels1 == {"Point"}
            is_simple_point2 = labels2 == {"Point"}

            # Complex point to/from simple point conversions with region costs
            base_cost = ChangesCost.NO_COST.value

            if "IntersectionPoint" in labels1 and is_simple_point2:
                base_cost = ChangesCost.CRITICAL.value
            elif is_simple_point1 and "IntersectionPoint" in labels2:
                base_cost = ChangesCost.CRITICAL.value
            elif "EndPoint" in labels1 and is_simple_point2:
                base_cost = ChangesCost.SEVERE.value
            elif is_simple_point1 and "EndPoint" in labels2:
                base_cost = ChangesCost.SEVERE.value
            elif "CornerPoint" in labels1 and is_simple_point2:
                base_cost = ChangesCost.MINOR.value
            elif is_simple_point1 and "CornerPoint" in labels2:
                base_cost = ChangesCost.MINOR.value
            # Complex point to complex point conversions
            elif any(
                label in labels1
                for label in ["IntersectionPoint", "EndPoint", "CornerPoint"]
            ) and any(
                label in labels2
                for label in ["IntersectionPoint", "EndPoint", "CornerPoint"]
            ):
                base_cost = ChangesCost.GENERAL.value
            # Vector type substitutions
            elif "VerticalVector" in labels1 and "HorizontalVector" in labels2:
                base_cost = ChangesCost.GENERAL.value
            elif "HorizontalVector" in labels1 and "VerticalVector" in labels2:
                base_cost = ChangesCost.GENERAL.value
            elif "VerticalVector" in labels1 and "DiagonalVector" in labels2:
                base_cost = ChangesCost.MINOR.value
            elif "DiagonalVector" in labels1 and "VerticalVector" in labels2:
                base_cost = ChangesCost.MINOR.value
            elif "HorizontalVector" in labels1 and "DiagonalVector" in labels2:
                base_cost = ChangesCost.MINOR.value
            elif "DiagonalVector" in labels1 and "HorizontalVector" in labels2:
                base_cost = ChangesCost.MINOR.value
            else:
                base_cost = ChangesCost.GENERAL.value
                logging.warning(
                    f"Unhandled substitution case between {labels1} and {labels2}"
                )


            return base_cost

        def node_del_cost(node_data: Dict) -> float:
            labels = node_data.get("labels", set())

            if "Segment" in labels:
                return ChangesCost.MINOR.value
            elif "IntersectionPoint" in labels:
                return ChangesCost.CRITICAL.value
            elif "EndPoint" in labels:
                return ChangesCost.GENERAL.value
            elif "CornerPoint" in labels:
                return ChangesCost.MINOR.value
            else:  # Point or Vector
                return ChangesCost.NO_COST.value

        def node_ins_cost(node_data: Dict) -> float:
            labels = node_data.get("labels", set())
            if "Segment" in labels:
                return ChangesCost.SEVERE.value
            elif any(
                label in labels
                for label in ["VerticalVector", "HorizontalVector", "DiagonalVector"]
            ):
                return ChangesCost.SEVERE.value

            return node_del_cost(node_data) * 2

        try:
            # Calculate GED with custom cost functions
            ged = nx.graph_edit_distance(
                image_graph,
                concept_graph,
                node_subst_cost=node_subst_cost,
                node_del_cost=node_del_cost,
                node_ins_cost=node_ins_cost,
                timeout=ged_timeout,
            )

            logger.info(f"GED: {ged}")

            if ged is None:  # Timeout occurred
                return 0.0

            # Convert GED to similarity score (inverse and normalize)
            max_possible_ged = max(len(image_graph) + len(concept_graph), 1)
            similarity = 1.0 - (ged / max_possible_ged)
            logging.info(f"GED: {ged}, max_possible_ged: {max_possible_ged}, similarity: {similarity}")
            return max(0.0, min(1.0, similarity))  # Ensure score is between 0 and 1

        except Exception as e:
            logging.error(f"Error calculating GED: {str(e)}")
            return 0.0
