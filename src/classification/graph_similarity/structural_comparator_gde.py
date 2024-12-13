import logging
from neo4j import Session
import networkx as nx
from typing import Dict, Any, Set, List, Tuple

from .neo4j_to_networkx import Neo4jToNetworkX

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class StructuralComparator:

    @staticmethod
    def compare_graphs_ged(
        session: Session,
        image_id: str,
        concept_id: str,
        concept_name: str,
        ged_timeout: float,
    ) -> float:
        logging.info(
            f"Comparing graph for image {image_id} with concept {concept_name} ({concept_id}) using Graph Edit Distance"
        )

        # Get original graphs
        image_graph = Neo4jToNetworkX.extract_image_graph(session, image_id)
        concept_graph = Neo4jToNetworkX.extract_concept_graph(session, concept_id)

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

        # Define node substitution cost
        def node_subst_cost(node1_data: Dict, node2_data: Dict) -> float:
            """Calculate substitution cost between two nodes based on their labels.
            
            Args:
                node1_data: Dictionary containing first node's data with labels
                node2_data: Dictionary containing second node's data with labels
                
            Returns:
                float: Cost of substituting node1 with node2
            """
            labels1 = node1_data.get("labels", set())
            labels2 = node2_data.get("labels", set())
            
            logging.info(f"Comparing node labels: {labels1} vs {labels2}")

            # If labels are identical, no cost
            if labels1 == labels2:
                logging.info("No substitution cost: 0.0")
                return 0.0
            
            is_simple_point1 = labels1 == {"Point"}
            is_simple_point2 = labels2 == {"Point"}
            
            # Complex point to/from simple point conversions
            if "IntersectionPoint" in labels1 and is_simple_point2:
                logging.info("Intersection Point to Point substitution cost: 20.0")
                return 20.0
            if is_simple_point1 and "IntersectionPoint" in labels2:
                logging.info("Point to Intersection Point substitution cost: 20.0")
                return 20.0
            
            if "EndPoint" in labels1 and is_simple_point2:
                logging.info("End Point to Point substitution cost: 5.0")
                return 5.0
            if is_simple_point1 and "EndPoint" in labels2:
                logging.info("Point to End Point substitution cost: 5.0")
                return 5.0
            
            if "CornerPoint" in labels1 and is_simple_point2:
                logging.info("Corner Point to Point substitution cost: 1.0")
                return 0.5
            if is_simple_point1 and "CornerPoint" in labels2:
                logging.info("Point to Corner Point substitution cost: 1.0")
                return 0.5
            
            # Complex point to complex point conversions
            if any(label in labels1 for label in ["IntersectionPoint", "EndPoint", "CornerPoint"]) and \
               any(label in labels2 for label in ["IntersectionPoint", "EndPoint", "CornerPoint"]):
                logging.info("Complex point to different complex point substitution cost: 5.0")
                return 5.0
            
            # Vector type substitutions
            if "VerticalVector" in labels1 and "HorizontalVector" in labels2:
                logging.info("Vertical to Horizontal Vector substitution cost: 5.0")
                return 5.0
            if "HorizontalVector" in labels1 and "VerticalVector" in labels2:
                logging.info("Horizontal to Vertical Vector substitution cost: 5.0")
                return 5.0
            
            # Diagonal vector substitutions
            if "VerticalVector" in labels1 and "DiagonalVector" in labels2:
                logging.info("Vertical to Diagonal Vector substitution cost: 1.0")
                return 1.0
            if "DiagonalVector" in labels1 and "VerticalVector" in labels2:
                logging.info("Diagonal to Vertical Vector substitution cost: 1.0")
                return 1.0
            
            if "HorizontalVector" in labels1 and "DiagonalVector" in labels2:
                logging.info("Horizontal to Diagonal Vector substitution cost: 1.0")
                return 1.0
            if "DiagonalVector" in labels1 and "HorizontalVector" in labels2:
                logging.info("Diagonal to Horizontal Vector substitution cost: 1.0")
                return 1.0

            # Default case for unhandled substitutions (high cost to penalize unexpected matches)
            logging.warning(f"Unhandled substitution case between {labels1} and {labels2}")
            return 10.0

        def node_del_cost(node_data: Dict) -> float:
            labels = node_data.get("labels", set())
            logging.info(f"Calculating deletion cost for node with labels: {labels}")

            if "IntersectionPoint" in labels:
                logging.info("Intersection Point deletion cost: 20.0")
                return 20.0
            elif "EndPoint" in labels:
                logging.info("End Point deletion cost: 5.0")
                return 5.0
            elif "CornerPoint" in labels:
                logging.info("Corner Point deletion cost: 1.0")
                return 1.0
            else:  # Point or Vector
                logging.info("Default deletion cost: 0.1")
                return 0.1

        def node_ins_cost(node_data: Dict) -> float:
            logging.info(f"Calculating insertion cost for node with labels: {node_data.get('labels', set())}")
            
            labels = node_data.get("labels", set())
            
            if any(label in labels for label in ["VerticalVector", "HorizontalVector", "DiagonalVector"]):
                logging.info("Vector insertion cost: 5.0")
                return 5.0
            
            return node_del_cost(node_data) * 2

        try:
            # Calculate GED with custom cost functions
            ged = nx.graph_edit_distance(
                image_graph,
                concept_graph,
                node_subst_cost=node_subst_cost,
                node_del_cost=node_del_cost,
                node_ins_cost=node_ins_cost,
                timeout=ged_timeout,  # Add timeout to prevent long computations
            )

            logger.info(f"GED: {ged}")

            if ged is None:  # Timeout occurred
                return 0.0

            # Convert GED to similarity score (inverse and normalize)
            max_possible_ged = max(
                len(image_graph) + len(concept_graph), 1
            )  # Avoid division by zero
            similarity = 1.0 - (ged / max_possible_ged)

            return max(0.0, min(1.0, similarity))  # Ensure score is between 0 and 1

        except Exception as e:
            logging.error(f"Error calculating GED: {str(e)}")
            return 0.0
