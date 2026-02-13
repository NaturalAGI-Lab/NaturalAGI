import logging
import networkx as nx

from .cost_functions import (
    node_subst_cost,
    node_del_cost,
    node_ins_cost,
    edge_match,
    edge_del_cost,
    edge_ins_cost,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GraphEditDistanceComparator:
    @staticmethod
    def log_edit_operations(paths, image_graph: nx.Graph, concept_graph: nx.Graph):
        if not paths:
            logger.info("No edit paths found")
            return

        node_path, edge_path = paths[0]

        logger.info("=" * 60)
        logger.info("GRAPH EDIT DISTANCE OPERATIONS")
        logger.info("=" * 60)

        # Log node operations
        logger.info("NODE OPERATIONS:")
        logger.info("-" * 60)
        logger.info(
            f"{'Operation':<15} {'Source Node':<15} {'Target Node':<15} {'Cost':<10}"
        )
        logger.info("-" * 60)

        total_node_cost = 0
        for node1, node2 in node_path:
            if node1 is None:  # Node insertion
                node2_data = concept_graph.nodes[node2]
                cost = node_ins_cost(node2_data)
                logger.info(f"{'INSERT':<15} {'None':<15} {str(node2):<15} {cost:<10}")
                total_node_cost += cost
            elif node2 is None:  # Node deletion
                node1_data = image_graph.nodes[node1]
                cost = node_del_cost(node1_data)
                logger.info(f"{'DELETE':<15} {str(node1):<15} {'None':<15} {cost:<10}")
                total_node_cost += cost
            else:  # Node substitution
                cost = node_subst_cost(
                    image_graph.nodes[node1], concept_graph.nodes[node2]
                )
                logger.info(
                    f"{'SUBSTITUTE':<15} {str(node1):<15} {str(node2):<15} {cost:<10}"
                )
                total_node_cost += cost

        logger.info("-" * 60)
        logger.info(f"{'TOTAL NODE COST:':<45} {total_node_cost:<10}")
        logger.info("")

        # Log edge operations
        logger.info("EDGE OPERATIONS:")
        logger.info("-" * 60)
        logger.info(
            f"{'Operation':<15} {'Source Edge':<20} {'Target Edge':<20} {'Cost':<10}"
        )
        logger.info("-" * 60)

        total_edge_cost = 0
        for edge1, edge2 in edge_path:
            if edge1 is None:  # Edge insertion
                edge2_data = concept_graph.edges[edge2]
                cost = edge_ins_cost(edge2_data)
                logger.info(f"{'INSERT':<15} {'None':<20} {str(edge2):<20} {cost:<10}")
                total_edge_cost += cost
            elif edge2 is None:  # Edge deletion
                edge1_data = image_graph.edges[edge1]
                cost = edge_del_cost(edge1_data)
                logger.info(f"{'DELETE':<15} {str(edge1):<20} {'None':<20} {cost:<10}")
                total_edge_cost += cost
            else:  # Edge substitution (if not matching)
                edge1_data = image_graph.edges[edge1]
                edge2_data = concept_graph.edges[edge2]
                if not edge_match(edge1_data, edge2_data):
                    cost = edge_del_cost(edge1_data) + edge_ins_cost(edge2_data)
                    logger.info(
                        f"{'SUBSTITUTE':<15} {str(edge1):<20} {str(edge2):<20} {cost:<10}"
                    )
                    total_edge_cost += cost
                else:
                    logger.info(
                        f"{'MATCH':<15} {str(edge1):<20} {str(edge2):<20} {0:<10}"
                    )

        logger.info("-" * 60)
        logger.info(f"{'TOTAL EDGE COST:':<45} {total_edge_cost:<10}")
        logger.info("-" * 60)
        logger.info(f"{'TOTAL COST:':<45} {total_node_cost + total_edge_cost:<10}")
        logger.info("=" * 60)

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

        try:
            # Calculate GED with custom cost functions
            paths, cost = nx.optimal_edit_paths(
                image_graph,
                concept_graph,
                node_subst_cost=node_subst_cost,
                node_del_cost=node_del_cost,
                node_ins_cost=node_ins_cost,
                edge_match=edge_match,
                edge_del_cost=edge_del_cost,
                edge_ins_cost=edge_ins_cost,
                # timeout=ged_timeout,
            )

            logger.info(f"GED: {cost}")

            # Log detailed edit operations
            GraphEditDistanceComparator.log_edit_operations(
                paths, image_graph, concept_graph
            )

            if cost is None:  # Timeout occurred
                return 0.0

            # Convert GED to similarity score (inverse and normalize)
            max_possible_cost = max(len(image_graph) + len(concept_graph), 1)
            similarity = 1.0 - (cost / max_possible_cost)
            similarity = round(similarity, 4)
            logging.info(
                f"GED: {cost}, max_possible_cost: {max_possible_cost}, similarity: {similarity}"
            )
            return max(0.0, min(1.0, similarity))  # Ensure score is between 0 and 1

        except Exception as e:
            logging.error(f"Error calculating GED: {str(e)}", exc_info=True)
            return 0.0
