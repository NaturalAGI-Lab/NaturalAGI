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
    MINOR = 0.5
    GENERAL = 1.0
    SEVERE = 5.0
    CRITICAL = 15.0
    IMPOSSIBLE = float("inf")

class StructuralComparator:
    # Region change costs lookup table
    REGION_CHANGE_COSTS: Dict[FrozenSet[str], float] = {
        # Vertical changes
        frozenset(["top", "center_horizontal"]): ChangesCost.MINOR.value,
        frozenset(["bottom", "center_horizontal"]): ChangesCost.MINOR.value,
        frozenset(["top", "bottom"]): ChangesCost.CRITICAL.value,
        # Horizontal changes
        frozenset(["left", "center_vertical"]): ChangesCost.MINOR.value,
        frozenset(["right", "center_vertical"]): ChangesCost.MINOR.value,
        frozenset(["left", "right"]): ChangesCost.CRITICAL.value,
        # Diagonal changes
        frozenset(["top", "left"]): ChangesCost.SEVERE.value,
        frozenset(["top", "right"]): ChangesCost.SEVERE.value,
        frozenset(["bottom", "left"]): ChangesCost.SEVERE.value,
        frozenset(["bottom", "right"]): ChangesCost.SEVERE.value,
    }

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

        def _calculate_region_change_cost(
            segments1: List[str], segments2: List[str]
        ) -> float:
            """Calculate cost of region changes"""
            seg_set1 = set(segments1)
            seg_set2 = set(segments2)

            # If segments are identical, no cost
            if seg_set1 == seg_set2:
                return ChangesCost.NO_COST.value

            # Calculate total cost of region changes
            total_cost = ChangesCost.NO_COST.value

            # Compare vertical components
            vertical1 = seg_set1 & {"top", "bottom", "center_horizontal"}
            vertical2 = seg_set2 & {"top", "bottom", "center_horizontal"}
            if vertical1 != vertical2:
                change_key = frozenset(vertical1 | vertical2)
                total_cost += StructuralComparator.REGION_CHANGE_COSTS.get(
                    change_key, ChangesCost.CRITICAL.value
                )

            # Compare horizontal components
            horizontal1 = seg_set1 & {"left", "right", "center_vertical"}
            horizontal2 = seg_set2 & {"left", "right", "center_vertical"}
            if horizontal1 != horizontal2:
                change_key = frozenset(horizontal1 | horizontal2)
                total_cost += StructuralComparator.REGION_CHANGE_COSTS.get(
                    change_key, ChangesCost.CRITICAL.value
                )

            return total_cost

        def node_subst_cost(node1_data: Dict, node2_data: Dict) -> float:
            """Calculate substitution cost between two nodes based on their labels and regions"""
            labels1 = node1_data.get("labels", set())
            labels2 = node2_data.get("labels", set())

            logging.info(f"Comparing node labels: {labels1} vs {labels2}")

            # Avoid vector-to-point comparisons
            is_vector1 = any("Vector" in label for label in labels1)
            is_vector2 = any("Vector" in label for label in labels2)
            if is_vector1 != is_vector2:
                return float("inf")

            # If labels are identical, check only regions
            if labels1 == labels2:
                region_cost = _calculate_region_change_cost(
                    node1_data.get("relative_segments", []),
                    node2_data.get("relative_segments", []),
                )
                logging.info(f"Same labels, region cost: {region_cost}")
                return region_cost

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

            # Add region change cost
            region_cost = _calculate_region_change_cost(
                node1_data.get("relative_segments", []),
                node2_data.get("relative_segments", []),
            )

            total_cost = base_cost + region_cost
            logging.info(
                f"Base cost: {base_cost}, Region cost: {region_cost}, Total: {total_cost}"
            )
            return total_cost

        def node_del_cost(node_data: Dict) -> float:
            labels = node_data.get("labels", set())
            logging.info(f"Calculating deletion cost for node with labels: {labels}")

            if "IntersectionPoint" in labels:
                return ChangesCost.CRITICAL.value
            elif "EndPoint" in labels:
                return ChangesCost.GENERAL.value
            elif "CornerPoint" in labels:
                return ChangesCost.MINOR.value
            else:  # Point or Vector
                return ChangesCost.NO_COST.value

        def node_ins_cost(node_data: Dict) -> float:
            logging.info(
                f"Calculating insertion cost for node with labels: {node_data.get('labels', set())}"
            )

            labels = node_data.get("labels", set())
            if any(
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

            return max(0.0, min(1.0, similarity))  # Ensure score is between 0 and 1

        except Exception as e:
            logging.error(f"Error calculating GED: {str(e)}")
            return 0.0
