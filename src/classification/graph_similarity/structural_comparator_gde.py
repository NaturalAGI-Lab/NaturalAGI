import logging
from neo4j import Session
import networkx as nx
from typing import Dict, Any, Set, List, Tuple

from .neo4j_to_networkx import Neo4jToNetworkX


class StructuralComparator:
    
    @staticmethod
    def compare_graphs_ged(
        session: Session, image_id: str, concept_id: str, concept_name: str, ged_timeout: float
    ) -> float:
        logging.info(
            f"Comparing graph for image {image_id} with concept {concept_name} ({concept_id}) using Graph Edit Distance"
        )

        # Get original graphs
        image_graph = Neo4jToNetworkX.extract_image_graph(session, image_id)
        concept_graph = Neo4jToNetworkX.extract_concept_graph(session, concept_id)

        # Compare at different abstraction levels
        scores = []

        # Level 1: Original structure
        original_score = StructuralComparator._compare_at_level(
            image_graph, concept_graph, abstraction_level="original", ged_timeout=ged_timeout
        )
        scores.append(("original", original_score))

        # # Level 2: Simplified structure (Intersection -> Corner)
        # simplified_score = StructuralComparator._compare_at_level(
        #     image_graph, concept_graph, abstraction_level="simplified", ged_timeout=ged_timeout
        # )
        # scores.append(("simplified", simplified_score))

        # # Level 3: Basic structure (all -> Point)
        # basic_score = StructuralComparator._compare_at_level(
        #     image_graph, concept_graph, abstraction_level="basic", ged_timeout=ged_timeout
        # )
        # scores.append(("basic", basic_score))

        # Get the best score
        best_score = max(scores, key=lambda x: x[1])
        logging.info(f"Comparison scores: {scores}")
        logging.info(f"Best score: {best_score[0]} - {best_score[1]}")

        return best_score[1]

    @staticmethod
    def _compare_at_level(
        image_graph: nx.Graph, concept_graph: nx.Graph, abstraction_level: str, ged_timeout: float
    ) -> float:
        """Compare graphs at a specific abstraction level using Graph Edit Distance"""
        # Create copies to modify
        img_graph = image_graph.copy()
        con_graph = concept_graph.copy()

        # Apply abstraction
        StructuralComparator._apply_abstraction(img_graph, abstraction_level)
        StructuralComparator._apply_abstraction(con_graph, abstraction_level)

        # Define node substitution cost
        def node_subst_cost(node1_data: Dict, node2_data: Dict) -> float:
            labels1 = node1_data.get("labels", set())
            labels2 = node2_data.get("labels", set())

            # If labels are identical, cost is 0
            if labels1 == labels2:
                return 0.0
            # If one set is subset of another, partial match
            elif labels1.intersection(labels2):
                return 0.5
            # Complete mismatch
            return 1.0
        
        def node_del_cost(node_data: Dict) -> float:
            labels = node_data.get("labels", set())
            if "IntersectionPoint" in labels:
                return 3.0
            return 1.0
        
        def node_ins_cost(node_data: Dict) -> float:
            labels = node_data.get("labels", set())
            if "IntersectionPoint" in labels:
                return 3.0
            return 1.0

        try:
            # Calculate GED with custom cost functions
            ged = nx.graph_edit_distance(
                img_graph,
                con_graph,
                node_subst_cost=node_subst_cost,
                node_del_cost=node_del_cost,
                node_ins_cost=node_ins_cost,
                timeout=ged_timeout,  # Add timeout to prevent long computations
            )

            if ged is None:  # Timeout occurred
                return 0.0

            # Convert GED to similarity score (inverse and normalize)
            max_possible_ged = max(
                len(img_graph) + len(con_graph), 1
            )  # Avoid division by zero
            similarity = 1.0 - (ged / max_possible_ged)

            return max(0.0, min(1.0, similarity))  # Ensure score is between 0 and 1

        except Exception as e:
            logging.error(f"Error calculating GED: {str(e)}")
            return 0.0

    @staticmethod
    def _apply_abstraction(graph: nx.Graph, level: str) -> None:
        """Apply abstraction rules to the graph based on level"""
        for node, data in list(graph.nodes(data=True)):
            labels = data.get("labels", set())

            # Only modify nodes that are some type of Point
            if any(label.endswith("Point") for label in labels):
                new_labels = set(labels)

                if level == "simplified":
                    # Convert Intersection points to Corner points
                    if "IntersectionPoint" in labels:
                        new_labels.remove("IntersectionPoint")
                        new_labels.add("CornerPoint")

                elif level == "basic":
                    # Remove specific point types and just keep Point
                    new_labels = {
                        label for label in labels if not label.endswith("Point")
                    }
                    new_labels.add("Point")

                # Update node labels only for Point nodes
                graph.nodes[node]["labels"] = new_labels
